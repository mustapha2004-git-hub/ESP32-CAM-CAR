#include <Arduino.h>
#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"

// ===========================
// WiFi credentials (2.4 GHz)
// ===========================
const char* ssid = "Mustapha00";
const char* password = "123456789";
// ===========================
// Tunable settings
// ===========================
#define STREAM_FRAME_SIZE  FRAMESIZE_VGA     // QVGA for max speed, VGA for detection
#define JPEG_QUALITY       12                // lower = better quality (10-15 good)
#define XCLK_FREQ          10000000
#define FRAME_DELAY_MS     15                // ~20-25 fps cap, keeps the chip cooler
#define WIFI_TX_POWER      WIFI_POWER_15dBm  // use 19_5dBm if the connection is unstable

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

httpd_handle_t ctrl_httpd   = NULL;   // port 80: page + commands
httpd_handle_t stream_httpd = NULL;   // port 81: video stream

// ---------- Drive command (fill in with your motor driver) ----------
// dir: F = forward, B = back, L = left, R = right, S = stop
void driveCar(char dir) {
  Serial.printf("CMD: %c\n", dir);
  // TODO: set your motor driver pins here (e.g. L298N / TB6612)
}

// ---------- Web page ----------
static esp_err_t index_handler(httpd_req_t *req) {
  const char* html =
    "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>ESP32-CAM Car</title></head>"
    "<body style='margin:0;background:#000;color:#0f0;text-align:center;font-family:monospace'>"
    "<img id='v' style='max-width:100%;height:auto'>"
    "<script>document.getElementById('v').src='http://'+location.hostname+':81/stream';</script>"
    "</body></html>";
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, html, strlen(html));
}

// ---------- Status: /status ----------
static esp_err_t status_handler(httpd_req_t *req) {
  char buf[200];
  snprintf(buf, sizeof(buf),
           "{\"psram\":%s,\"psram_free_kb\":%u,\"rssi\":%d,\"heap_kb\":%u}",
           psramFound() ? "true" : "false",
           (unsigned)(ESP.getFreePsram() / 1024),
           WiFi.RSSI(),
           (unsigned)(ESP.getFreeHeap() / 1024));
  httpd_resp_set_type(req, "application/json");
  return httpd_resp_send(req, buf, strlen(buf));
}

// ---------- Single frame: /capture ----------
static esp_err_t capture_handler(httpd_req_t *req) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }
  httpd_resp_set_type(req, "image/jpeg");
  esp_err_t res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return res;
}

// ---------- Commands: /cmd?d=F ----------
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

// ---------- MJPEG stream (port 81) ----------
static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t *fb = NULL;
  esp_err_t res = ESP_OK;
  char part_buf[64];

  res = httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=frame");
  if (res != ESP_OK) return res;
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  int frames = 0;
  unsigned long lastFpsPrint = millis();

  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      res = ESP_FAIL;
      break;
    }

    size_t hlen = snprintf(part_buf, sizeof(part_buf),
                           "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
                           (unsigned)fb->len);

    res = httpd_resp_send_chunk(req, "--frame\r\n", 9);
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, part_buf, hlen);
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, "\r\n", 2);

    esp_camera_fb_return(fb);
    fb = NULL;

    if (res != ESP_OK) break;   // client disconnected

    frames++;
    if (millis() - lastFpsPrint >= 3000) {
      Serial.printf("FPS: %.1f\n", frames * 1000.0 / (millis() - lastFpsPrint));
      frames = 0;
      lastFpsPrint = millis();
    }

    if (FRAME_DELAY_MS > 0) vTaskDelay(pdMS_TO_TICKS(FRAME_DELAY_MS));
  }
  return res;
}

void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  config.stack_size  = 8192;

  httpd_uri_t index_uri   = { "/",        HTTP_GET, index_handler,   NULL };
  httpd_uri_t status_uri  = { "/status",  HTTP_GET, status_handler,  NULL };
  httpd_uri_t capture_uri = { "/capture", HTTP_GET, capture_handler, NULL };
  httpd_uri_t cmd_uri     = { "/cmd",     HTTP_GET, cmd_handler,     NULL };

  if (httpd_start(&ctrl_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(ctrl_httpd, &index_uri);
    httpd_register_uri_handler(ctrl_httpd, &status_uri);
    httpd_register_uri_handler(ctrl_httpd, &capture_uri);
    httpd_register_uri_handler(ctrl_httpd, &cmd_uri);
  }

  // Stream server on its own port so it never blocks the commands
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

  pinMode(FLASH_LED_GPIO, OUTPUT);
  digitalWrite(FLASH_LED_GPIO, LOW);   // flash LED off

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = XCLK_FREQ;
  config.pixel_format = PIXFORMAT_JPEG;
  config.jpeg_quality = JPEG_QUALITY;

  if (psramFound()) {
    Serial.println("PSRAM found");
    config.frame_size  = FRAMESIZE_UXGA;   // init big, shrink after init
    config.fb_count    = 2;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.grab_mode   = CAMERA_GRAB_LATEST;   // always the newest frame
  } else {
    Serial.println("WARNING: PSRAM not found! Enable it in Tools -> PSRAM");
    config.frame_size  = FRAMESIZE_SVGA;
    config.fb_count    = 1;
    config.fb_location = CAMERA_FB_IN_DRAM;
    config.grab_mode   = CAMERA_GRAB_WHEN_EMPTY;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    return;
  }

  sensor_t *s = esp_camera_sensor_get();
  Serial.printf("Sensor PID: 0x%x (OV5640 = 0x5640)\n", s->id.PID);

  s->set_framesize(s, psramFound() ? STREAM_FRAME_SIZE : FRAMESIZE_QVGA);
  s->set_quality(s, JPEG_QUALITY);
  s->set_whitebal(s, 1);
  s->set_awb_gain(s, 1);
  s->set_wb_mode(s, 0);
  s->set_exposure_ctrl(s, 1);
  s->set_aec2(s, 1);
  s->set_gain_ctrl(s, 1);
  s->set_lenc(s, 1);
  s->set_bpc(s, 1);
  s->set_wpc(s, 1);
  s->set_brightness(s, 1);
  s->set_saturation(s, 0);
  s->set_sharpness(s, 1);

  // If the image is upside down or mirrored, uncomment:
  // s->set_vflip(s, 1);
  // s->set_hmirror(s, 1);

  // ---------- WiFi ----------
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setTxPower(WIFI_POWER_19_5dBm);   // full power while connecting

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
  WiFi.setTxPower(WIFI_TX_POWER);        // lower power after connecting (less heat)
  Serial.printf("WiFi signal (RSSI): %d dBm\n", WiFi.RSSI());

  startCameraServer();

  Serial.print("Camera Ready! Open http://");
  Serial.println(WiFi.localIP());
  Serial.println("Stream: http://<ip>:81/stream   Frame: http://<ip>/capture   Command: http://<ip>/cmd?d=F");
}

void loop() {
  delay(10000);
}