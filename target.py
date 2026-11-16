import cv2
a = cv2.aruco
img = a.generateImageMarker(a.getPredefinedDictionary(a.DICT_4X4_50), 0, 600)
cv2.imwrite("marker0.png", img)