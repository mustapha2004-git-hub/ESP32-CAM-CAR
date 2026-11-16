#include <Arduino.h>
#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"

// ===========================
// WiFi credentials (2.4 GHz)
// ===========================
const char* ssid     = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";

// ===========================
// Camera / heat settings
// ===========================
#define XCLK_FREQ          10000000
#define STREAM_FRAME_SIZE  FRAMESIZE_QVGA
#define JPEG_QUALITY       12
#define FRAME_DELAY_MS     40
#define LOW_IO_DRIVE       1
#define WIFI_TX_POWER      WIFI_POWER_15dBm

// ===========================
// Motor driver pins (TB6612 / DRV8833, 4 direction pins)
// ===========================
#define LEFT_IN1   13
#define LEFT_IN2   15
#define RIGHT_IN1  14
#define RIGHT_IN2   2
#define SWAP_LEFT_RIGHT_DIRECTION 0   // set to 1 if a side spins the wrong way
#define CMD_TIMEOUT_MS  300           // car stops if no command arrives for this long

// ===========================
// AI-Thinker ESP32-CAM pins
// ===========================
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22
#define FLASH_LED_GPIO     4

httpd_handle_t ctrl_httpd   = NULL;
httpd_handle_t stream_httpd = NULL;

camera_config_t camConfig;
volatile bool cameraOn = false;
volatile unsigned long lastCmdMs = 0;
volatile bool moving = false;

// ---------- Motors ----------
void setMotor(int in1, int in2, int dir) {   // dir: 1 forward, -1 backward, 0 stop
#if SWAP_LEFT_RIGHT_DIRECTION
  dir = -dir;
#endif
  digitalWrite(in1, dir > 0 ? HIGH : LOW);
  digitalWrite(in2, dir < 0 ? HIGH : LOW);
}

void driveCar(char dir) {
  switch (dir) {
    case 'F': setMotor(LEFT_IN1, LEFT_IN2,  1); setMotor(RIGHT_IN1, RIGHT_IN2,  1); break;
    case 'B': setMotor(LEFT_IN1, LEFT_IN2, -1); setMotor(RIGHT_IN1, RIGHT_IN2, -1); break;
    case 'L': setMotor(LEFT_IN1, LEFT_IN2, -1); setMotor(RIGHT_IN1, RIGHT_IN2,  1); break;  // spin left
    case 'R': setMotor(LEFT_IN1, LEFT_IN2,  1); setMotor(RIGHT_IN1, RIGHT_IN2, -1); break;  // spin right
    default:  setMotor(LEFT_IN1, LEFT_IN2,  0); setMotor(RIGHT_IN1, RIGHT_IN2,  0); dir = 'S'; break;
  }
  moving = (dir != 'S');
  lastCmdMs = millis();
  Serial.printf("CMD: %c\n", dir);
}

// ---------- Camera on / off ----------
bool cameraStart() {
  if (cameraOn) return true;
  pinMode(PWDN_GPIO_NUM, OUTPUT);
  digitalWrite(PWDN_GPIO_NUM, LOW);
  delay(50);

  esp_err_t err = esp_camera_init(&camConfig);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return false;
  }
  sensor_t *s = esp_camera_sensor_get();
  s->set_framesize(s, STREAM_FRAME_SIZE);
  s->set_quality(s, JPEG_QUALITY);
  s->set_whitebal(s, 1);
  s->set_awb_gain(s, 1);
  s->set_exposure_ctrl(s, 1);
  s->set_gain_ctrl(s, 1);
  s->set_lenc(s, 1);
  s->set_bpc(s, 1);
  s->set_wpc(s, 1);
#if LOW_IO_DRIVE
  if (s->id.PID == OV5640_PID) s->set_reg(s, 0x302C, 0xC0, 0x00);
#endif
  // s->set_vflip(s, 1);      // uncomment if the image is upside down
  // s->set_hmirror(s, 1);
  cameraOn = true;
  return true;
}

void cameraStop() {
  if (!cameraOn) return;
  esp_camera_deinit();
  pinMode(PWDN_GPIO_NUM, OUTPUT);
  digitalWrite(PWDN_GPIO_NUM, HIGH);
  cameraOn = false;
}

// ---------- Web handlers ----------
static esp_err_t index_handler(httpd_req_t *req) {
  const char* html =
    "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>ESP32-CAM Car</title></head>"
    "<body style='margin:0;background:#000;color:#0f0;text-align:center;font-family:monospace'>"
    "<p><a style='color:#0f0' href='/on'>camera ON</a> | <a style='color:#0f0' href='/off'>camera OFF</a> | "
    "<a style='color:#0f0' href='/status'>status</a></p>"
    "<img id='v' style='max-width:100%;height:auto'>"
    "<script>document.getElementById('v').src='http://'+location.hostname+':81/stream';</script>"
    "</body></html>";
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, html, strlen(html));
}

static esp_err_t on_handler(httpd_req_t *req) {
  bool ok = cameraStart();
  httpd_resp_send(req, ok ? "camera on" : "camera init failed", HTTPD_RESP_USE_STRLEN);
  return ESP_OK;
}

static esp_err_t off_handler(httpd_req_t *req) {
  cameraStop();
  httpd_resp_send(req, "camera off", HTTPD_RESP_USE_STRLEN);
  return ESP_OK;
}

static esp_err_t status_handler(httpd_req_t *req) {
  char buf[200];
  snprintf(buf, sizeof(buf),
           "{\"camera\":%s,\"uptime_s\":%lu,\"rssi\":%d,\"heap_kb\":%u}",
           cameraOn ? "true" : "false", millis() / 1000, WiFi.RSSI(),
           (unsigned)(ESP.getFreeHeap() / 1024));
  httpd_resp_set_type(req, "application/json");
  return httpd_resp_send(req, buf, strlen(buf));
}

static esp_err_t capture_handler(httpd_req_t *req) {
  if (!cameraOn && !cameraStart()) { httpd_resp_send_500(req); return ESP_FAIL; }
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) { httpd_resp_send_500(req); return ESP_FAIL; }
  httpd_resp_set_type(req, "image/jpeg");
  esp_err_t res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return res;
}

static esp_err_t cmd_handler(httpd_req_t *req) {
  char query[32], val[8];
  if (httpd_req_get_url_query_str(req, query, sizeof(query)) == ESP_OK &&
      httpd_query_key_value(query, "d", val, sizeof(val)) == ESP_OK) {
    driveCar(val[0]);
    httpd_resp_send(req, "OK", 2);
    return ESP_OK;
  }
  httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "use /cmd?d=F|B|L|R|S");
  return ESP_FAIL;
}

static esp_err_t stream_handler(httpd_req_t *req) {
  if (!cameraOn && !cameraStart()) { httpd_resp_send_500(req); return ESP_FAIL; }

  camera_fb_t *fb = NULL;
  esp_err_t res = ESP_OK;
  char part_buf[64];

  res = httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=frame");
  if (res != ESP_OK) return res;
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  while (cameraOn) {
    fb = esp_camera_fb_get();
    if (!fb) { res = ESP_FAIL; break; }

    size_t hlen = snprintf(part_buf, sizeof(part_buf),
                           "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", (unsigned)fb->len);
    res = httpd_resp_send_chunk(req, "--frame\r\n", 9);
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, part_buf, hlen);
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, "\r\n", 2);
    esp_camera_fb_return(fb);
    fb = NULL;
    if (res != ESP_OK) break;

    if (FRAME_DELAY_MS > 0) vTaskDelay(pdMS_TO_TICKS(FRAME_DELAY_MS));
  }
  return res;
}

void startServers() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  config.stack_size  = 8192;

  httpd_uri_t uris[] = {
    { "/",        HTTP_GET, index_handler,   NULL },
    { "/on",      HTTP_GET, on_handler,      NULL },
    { "/off",     HTTP_GET, off_handler,     NULL },
    { "/status",  HTTP_GET, status_handler,  NULL },
    { "/capture", HTTP_GET, capture_handler, NULL },
    { "/cmd",     HTTP_GET, cmd_handler,     NULL },
  };
  if (httpd_start(&ctrl_httpd, &config) == ESP_OK) {
    for (auto &u : uris) httpd_register_uri_handler(ctrl_httpd, &u);
  }

  config.server_port += 1;   // 81
  config.ctrl_port   += 1;
  httpd_uri_t stream_uri = { "/stream", HTTP_GET, stream_handler, NULL };
  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println();

  // Motors first, always stopped at boot
  int pins[] = { LEFT_IN1, LEFT_IN2, RIGHT_IN1, RIGHT_IN2 };
  for (int p : pins) { pinMode(p, OUTPUT); digitalWrite(p, LOW); }

  pinMode(FLASH_LED_GPIO, OUTPUT);
  digitalWrite(FLASH_LED_GPIO, LOW);

  pinMode(PWDN_GPIO_NUM, OUTPUT);
  digitalWrite(PWDN_GPIO_NUM, HIGH);

  camConfig.ledc_channel = LEDC_CHANNEL_0;
  camConfig.ledc_timer   = LEDC_TIMER_0;
  camConfig.pin_d0 = Y2_GPIO_NUM;
  camConfig.pin_d1 = Y3_GPIO_NUM;
  camConfig.pin_d2 = Y4_GPIO_NUM;
  camConfig.pin_d3 = Y5_GPIO_NUM;
  camConfig.pin_d4 = Y6_GPIO_NUM;
  camConfig.pin_d5 = Y7_GPIO_NUM;
  camConfig.pin_d6 = Y8_GPIO_NUM;
  camConfig.pin_d7 = Y9_GPIO_NUM;
  camConfig.pin_xclk     = XCLK_GPIO_NUM;
  camConfig.pin_pclk     = PCLK_GPIO_NUM;
  camConfig.pin_vsync    = VSYNC_GPIO_NUM;
  camConfig.pin_href     = HREF_GPIO_NUM;
  camConfig.pin_sccb_sda = SIOD_GPIO_NUM;
  camConfig.pin_sccb_scl = SIOC_GPIO_NUM;
  camConfig.pin_pwdn     = PWDN_GPIO_NUM;
  camConfig.pin_reset    = RESET_GPIO_NUM;
  camConfig.xclk_freq_hz = XCLK_FREQ;
  camConfig.pixel_format = PIXFORMAT_JPEG;
  camConfig.jpeg_quality = JPEG_QUALITY;
  camConfig.frame_size   = FRAMESIZE_UXGA;
  camConfig.fb_location  = CAMERA_FB_IN_PSRAM;
  camConfig.fb_count     = 1;
  camConfig.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;

  if (!psramFound()) {
    Serial.println("WARNING: PSRAM not found!");
    camConfig.frame_size  = FRAMESIZE_QVGA;
    camConfig.fb_location = CAMERA_FB_IN_DRAM;
  }

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setTxPower(WIFI_POWER_19_5dBm);
  Serial.printf("Connecting to \"%s\"", ssid);
  WiFi.begin(ssid, password);

  int tries = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    if (++tries % 20 == 0) {
      Serial.printf("\nStatus code: %d, retrying...\n", WiFi.status());
      WiFi.disconnect();
      delay(100);
      WiFi.begin(ssid, password);
    }
  }
  Serial.println("\nWiFi connected");
  WiFi.setTxPower(WIFI_TX_POWER);
  Serial.printf("RSSI: %d dBm\n", WiFi.RSSI());

  startServers();

  Serial.print("Ready: http://");
  Serial.println(WiFi.localIP());
}

void loop() {
  // Failsafe: stop the motors if the PC stops sending commands
  if (moving && (millis() - lastCmdMs > CMD_TIMEOUT_MS)) {
    driveCar('S');
  }
  // WiFi lost: stop and try to reconnect
  if (WiFi.status() != WL_CONNECTED) {
    driveCar('S');
    WiFi.reconnect();
    delay(1000);
  }
  delay(20);
}