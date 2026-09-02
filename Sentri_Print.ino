// ======================================================
// SENTRIPRINT - ESP32 HTTP POST TEST
// ======================================================

// WiFi.h allows the ESP32 to connect to a Wi-Fi network.
#include <WiFi.h>

// HTTPClient.h allows the ESP32 to communicate
// with web servers using HTTP.
#include <HTTPClient.h>


// ======================================================
// 1. WI-FI SETTINGS
// ======================================================

// Replace this with the name of your Wi-Fi network.
const char* ssid = "Dera";

// Replace this with your Wi-Fi password.
//
// IMPORTANT:
// Don't send your actual password to me.
const char* password = "bbbbbbbh";


// ======================================================
// 2. TEST SERVER
// ======================================================

// This is a temporary test server.
//
// We are using it to learn how the ESP32 sends
// data to a server using HTTP POST.
//
// This is NOT the final SentriPrint server.
const char* serverURL = "http://10.212.239.199:8000/attendance";


void setup() {
  // put your setup code here, to run once:

   Serial.begin(115200);


  // ----------------------------------------------------
  // Display SentriPrint information
  // ----------------------------------------------------

  Serial.println();
  Serial.println("================================");
  Serial.println("       SENTRI-PRINT ESP32");
  Serial.println("================================");


  // ----------------------------------------------------
  // CONNECT TO WI-FI
  // ----------------------------------------------------

  Serial.print("Connecting to Wi-Fi");

  // Tell the ESP32 to connect to our Wi-Fi network.
  WiFi.begin(ssid, password);


  // Keep checking until the ESP32 connects.
  while (WiFi.status() != WL_CONNECTED) {

    // Print a dot every 500 milliseconds so we
    // know that the ESP32 is still trying to connect.
    Serial.print(".");

    delay(500);
  }


  // If the program reaches here, Wi-Fi connected.
  Serial.println();
  Serial.println("Wi-Fi connected!");


  // Display the IP address assigned to the ESP32.
  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());


  // ====================================================
  // CREATE HTTP CLIENT
  // ====================================================

  // Create an HTTPClient object.
  //
  // Think of 'http' as our tool for communicating
  // with the web server.
  HTTPClient http;


  // ====================================================
  // CONNECT TO THE SERVER
  // ====================================================

  // Tell the HTTP client which server we want
  // to communicate with.
  http.begin(serverURL);


  // ====================================================
  // TELL THE SERVER WE ARE SENDING JSON
  // ====================================================

  // HTTP headers provide information about our request.
  //
  // This tells the server:
  // "The data I'm sending is JSON."
  http.addHeader("Content-Type", "application/json");


  // ====================================================
  // CREATE SIMULATED ATTENDANCE DATA
  // ====================================================

  // We don't have the fingerprint sensor yet.
  //
  // So for now, we're pretending that a fingerprint
  // with ID 23 was scanned.
  String jsonData = "{";

  // Student ID.
  jsonData += "\"student_id\":\"STU001\",";

  // Simulated fingerprint ID.
  jsonData += "\"fingerprint_id\":23,";

  // Unique ID for this SentriPrint device.
  jsonData += "\"device_id\":\"SENTRIPRINT-001\"";

  // Close the JSON object.
  jsonData += "}";


  // Display the information we're about to send.
  Serial.println();
  Serial.println("Data being sent:");
  Serial.println(jsonData);


  // ====================================================
  // SEND HTTP POST REQUEST
  // ====================================================

  // Send the JSON data to the server using HTTP POST.
  //
  // POST means:
  // "Server, I am sending you some information."
  int responseCode = http.POST(jsonData);


  // ====================================================
  // CHECK SERVER RESPONSE
  // ====================================================

  if (responseCode > 0) {

    // Display the HTTP response code.
    Serial.print("HTTP Response Code: ");
    Serial.println(responseCode);


    // Get the response sent back by the server.
    String response = http.getString();


    // Display the server response.
    Serial.println();
    Serial.println("Server Response:");
    Serial.println(response);

  } else {

    // If the response code is negative,
    // the HTTP request failed.
    Serial.print("HTTP Request Failed. Error: ");
    Serial.println(responseCode);
  }


  // ====================================================
  // CLOSE HTTP CONNECTION
  // ====================================================

  // Release the resources used by the HTTP connection.
  http.end();
}



void loop() {
  // put your main code here, to run repeatedly:

}
