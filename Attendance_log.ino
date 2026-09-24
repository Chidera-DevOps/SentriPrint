#include <Adafruit_Fingerprint.h>

// ============================================================
// AS608 CONNECTION
// ============================================================

// AS608 TX -> ESP32 GPIO16 (RX)
// AS608 RX -> ESP32 GPIO17 (TX)

HardwareSerial fingerprintSerial(2);

Adafruit_Fingerprint finger =
  Adafruit_Fingerprint(&fingerprintSerial);


// ============================================================
// FUNCTION DECLARATIONS
// ============================================================

void showMenu();
void showStorageCount();
int readID();
bool checkFingerprintID(int id);

void enrollFingerprint();
void checkID();
void deleteID();
void searchFingerprint();
void showStorageInfo();
void emptyDatabase();

void waitForFingerRemoval();


// ============================================================
// SETUP
// ============================================================

void setup() {

  Serial.begin(115200);

  delay(1000);

  Serial.println();
  Serial.println("========================================");
  Serial.println("       AS608 FINGERPRINT MANAGER");
  Serial.println("========================================");

  // Start UART communication with AS608.
  fingerprintSerial.begin(
    57600,
    SERIAL_8N1,
    16,
    17
  );

  finger.begin(57600);


  // ----------------------------------------------------------
  // Verify sensor
  // ----------------------------------------------------------

  Serial.println();
  Serial.println("Checking AS608...");

  if (finger.verifyPassword()) {

    Serial.println("[OK] AS608 detected.");

  } else {

    Serial.println("[ERROR] AS608 not detected.");
    Serial.println("Check TX/RX wiring and power.");

    while (true) {
      delay(1000);
    }
  }


  // ----------------------------------------------------------
  // Get sensor parameters
  // ----------------------------------------------------------

  finger.getParameters();

  Serial.print("Sensor capacity: ");
  Serial.println(finger.capacity);

  Serial.print("Security level: ");
  Serial.println(finger.security_level);

  Serial.print("Packet length: ");
  Serial.println(finger.packet_len);


  // ----------------------------------------------------------
  // Show stored fingerprints
  // ----------------------------------------------------------

  showStorageCount();

  showMenu();
}


// ============================================================
// MAIN LOOP
// ============================================================

void loop() {

  if (!Serial.available()) {
    return;
  }

  // Read only the command character.
  char command = Serial.read();


  // ----------------------------------------------------------
  // IMPORTANT SERIAL FIX
  //
  // If Serial Monitor is configured to send:
  //
  //     Newline
  //     Carriage return
  //     Both NL & CR
  //
  // selecting "6" can leave \r and/or \n in the buffer.
  //
  // We remove those characters before entering the function.
  // This is critical for the DELETE ALL confirmation.
  // ----------------------------------------------------------

  while (Serial.available() > 0) {
    Serial.read();
  }


  // Ignore line endings.
  if (command == '\n' || command == '\r') {
    return;
  }


  // ----------------------------------------------------------
  // COMMAND HANDLER
  // ----------------------------------------------------------

  switch (command) {

    case '1':
      enrollFingerprint();
      break;


    case '2':
      checkID();
      break;


    case '3':
      deleteID();
      break;


    case '4':
      searchFingerprint();
      break;


    case '5':
      showStorageInfo();
      break;


    case '6':
      emptyDatabase();
      break;


    case 'm':
    case 'M':
      showMenu();
      break;


    default:

      Serial.println();
      Serial.println("[ERROR] Unknown command.");

      showMenu();

      break;
  }
}


// ============================================================
// MENU
// ============================================================

void showMenu() {

  Serial.println();
  Serial.println("========================================");
  Serial.println("              MENU");
  Serial.println("========================================");

  Serial.println("1 - Enroll / Save fingerprint");
  Serial.println("2 - Check if an ID exists");
  Serial.println("3 - Delete an ID");
  Serial.println("4 - Search a fingerprint");
  Serial.println("5 - Show storage information");
  Serial.println("6 - DELETE ALL fingerprints");
  Serial.println("M - Show menu");

  Serial.println("========================================");

  showStorageCount();

  Serial.println("========================================");
  Serial.println("Enter command:");
}


// ============================================================
// SHOW NUMBER OF STORED FINGERPRINTS
// ============================================================

void showStorageCount() {

  uint8_t result = finger.getTemplateCount();

  if (result == FINGERPRINT_OK) {

    Serial.print("Stored fingerprints: ");
    Serial.println(finger.templateCount);

  } else {

    Serial.println(
      "[WARNING] Could not read stored fingerprint count."
    );
  }
}


// ============================================================
// READ ID
// ============================================================

int readID() {

  Serial.println();
  Serial.print("Enter fingerprint ID (1-");
  Serial.print(finger.capacity);
  Serial.println("):");


  // ----------------------------------------------------------
  // Wait for input
  // ----------------------------------------------------------

  while (!Serial.available()) {
    delay(10);
  }


  int id = Serial.parseInt();


  // ----------------------------------------------------------
  // Clear everything remaining in Serial buffer.
  // ----------------------------------------------------------

  while (Serial.available() > 0) {
    Serial.read();
  }


  // ----------------------------------------------------------
  // Validate ID
  // ----------------------------------------------------------

  if (id < 1 || id > finger.capacity) {

    Serial.println();
    Serial.println("[ERROR] Invalid ID.");

    return -1;
  }


  return id;
}


// ============================================================
// CHECK WHETHER A FINGERPRINT EXISTS AT AN ID
// ============================================================

bool checkFingerprintID(int id) {

  uint8_t result = finger.loadModel(id);

  if (result == FINGERPRINT_OK) {
    return true;
  }

  return false;
}


// ============================================================
// ENROLL FINGERPRINT
// ============================================================

void enrollFingerprint() {

  int id = readID();

  if (id == -1) {

    showMenu();

    return;
  }


  // ----------------------------------------------------------
  // Check whether ID is already occupied
  // ----------------------------------------------------------

  Serial.println();
  Serial.print("Checking ID ");
  Serial.print(id);
  Serial.println("...");


  if (checkFingerprintID(id)) {

    Serial.println();
    Serial.println("========================================");
    Serial.println("          ID ALREADY EXISTS");
    Serial.println("========================================");

    Serial.print("ID ");
    Serial.print(id);
    Serial.println(" already contains a fingerprint.");

    Serial.println();
    Serial.println("Choose another ID.");

    showMenu();

    return;
  }


  // ----------------------------------------------------------
  // Start enrollment
  // ----------------------------------------------------------

  Serial.println();
  Serial.println("========================================");

  Serial.print("    ENROLLING FINGERPRINT → ID ");
  Serial.println(id);

  Serial.println("========================================");


  uint8_t result;


  // ==========================================================
  // FIRST SCAN
  // ==========================================================

  Serial.println();
  Serial.println("Place the finger on the sensor...");


  while (true) {

    result = finger.getImage();


    if (result == FINGERPRINT_OK) {

      Serial.println("[OK] Finger detected.");

      break;
    }


    if (result != FINGERPRINT_NOFINGER) {

      Serial.print(
        "[ERROR] Could not capture fingerprint. Code: "
      );

      Serial.println(result);

      showMenu();

      return;
    }


    delay(100);
  }


  // ----------------------------------------------------------
  // Convert first image
  // ----------------------------------------------------------

  result = finger.image2Tz(1);


  if (result != FINGERPRINT_OK) {

    Serial.print(
      "[ERROR] First fingerprint conversion failed. Code: "
    );

    Serial.println(result);

    waitForFingerRemoval();

    showMenu();

    return;
  }


  Serial.println(
    "[OK] First fingerprint converted."
  );


  // ==========================================================
  // REMOVE FINGER
  // ==========================================================

  Serial.println();
  Serial.println("Remove your finger...");


  while (finger.getImage() != FINGERPRINT_NOFINGER) {

    delay(100);
  }


  Serial.println("[OK] Finger removed.");

  delay(700);


  // ==========================================================
  // SECOND SCAN
  // ==========================================================

  Serial.println();
  Serial.println("Place the SAME finger again...");


  while (true) {

    result = finger.getImage();


    if (result == FINGERPRINT_OK) {

      Serial.println("[OK] Finger detected.");

      break;
    }


    if (result != FINGERPRINT_NOFINGER) {

      Serial.print(
        "[ERROR] Could not capture second fingerprint. Code: "
      );

      Serial.println(result);

      showMenu();

      return;
    }


    delay(100);
  }


  // ----------------------------------------------------------
  // Convert second image
  // ----------------------------------------------------------

  result = finger.image2Tz(2);


  if (result != FINGERPRINT_OK) {

    Serial.print(
      "[ERROR] Second fingerprint conversion failed. Code: "
    );

    Serial.println(result);

    waitForFingerRemoval();

    showMenu();

    return;
  }


  Serial.println(
    "[OK] Second fingerprint converted."
  );


  // ==========================================================
  // CREATE MODEL
  // ==========================================================

  Serial.println();
  Serial.println("Creating fingerprint model...");


  result = finger.createModel();


  if (result == FINGERPRINT_OK) {

    Serial.println(
      "[OK] Two scans matched."
    );

    Serial.println(
      "[OK] Fingerprint model created."
    );

  } else {

    Serial.print(
      "[ERROR] Could not create fingerprint model. Code: "
    );

    Serial.println(result);


    if (result == FINGERPRINT_ENROLLMISMATCH) {

      Serial.println(
        "The two fingerprints did not match."
      );

      Serial.println(
        "Please restart enrollment and use the same finger."
      );
    }


    waitForFingerRemoval();

    showMenu();

    return;
  }


  // ==========================================================
  // SAVE MODEL
  // ==========================================================

  Serial.println();
  Serial.print("Saving fingerprint to ID ");
  Serial.println(id);


  result = finger.storeModel(id);


  if (result == FINGERPRINT_OK) {

    Serial.println();
    Serial.println("========================================");
    Serial.println("       FINGERPRINT SAVED");
    Serial.println("========================================");

    Serial.print("Fingerprint ID: ");
    Serial.println(id);

    Serial.println();
    Serial.println("The fingerprint is now stored");
    Serial.println("inside the AS608.");

    showStorageCount();

  } else {

    Serial.println();
    Serial.println("========================================");
    Serial.println("          SAVE FAILED");
    Serial.println("========================================");

    Serial.print("Error code: ");
    Serial.println(result);
  }


  waitForFingerRemoval();

  delay(500);

  showMenu();
}


// ============================================================
// CHECK ID
// ============================================================

void checkID() {

  int id = readID();

  if (id == -1) {

    showMenu();

    return;
  }


  Serial.println();
  Serial.print("Checking ID ");
  Serial.println(id);


  uint8_t result = finger.loadModel(id);


  if (result == FINGERPRINT_OK) {

    Serial.println();
    Serial.println("========================================");
    Serial.println("             ID EXISTS");
    Serial.println("========================================");

    Serial.print("Fingerprint ID ");
    Serial.print(id);

    Serial.println(
      " contains a stored template."
    );

  } else {

    Serial.println();
    Serial.println("========================================");
    Serial.println("           ID NOT FOUND");
    Serial.println("========================================");

    Serial.print("Fingerprint ID ");
    Serial.print(id);

    Serial.println(
      " does not contain a stored template."
    );
  }


  showMenu();
}


// ============================================================
// DELETE ONE ID
// ============================================================

void deleteID() {

  int id = readID();

  if (id == -1) {

    showMenu();

    return;
  }


  // ----------------------------------------------------------
  // Check whether ID exists
  // ----------------------------------------------------------

  Serial.println();
  Serial.print("Checking ID ");
  Serial.println(id);


  if (!checkFingerprintID(id)) {

    Serial.println();
    Serial.println(
      "[INFO] No fingerprint exists at this ID."
    );

    showMenu();

    return;
  }


  // ==========================================================
  // CONFIRMATION
  // ==========================================================

  Serial.println();
  Serial.println("========================================");
  Serial.println("          DELETE FINGERPRINT");
  Serial.println("========================================");

  Serial.print("Fingerprint ID ");
  Serial.print(id);
  Serial.println(" exists.");

  Serial.print("Delete ID ");
  Serial.print(id);
  Serial.println("?");

  Serial.println();

  Serial.println("Type Y and press Enter to confirm.");
  Serial.println("Type N and press Enter to cancel.");


  // ----------------------------------------------------------
  // IMPORTANT:
  //
  // Remove anything left over from the ID input.
  // ----------------------------------------------------------

  while (Serial.available() > 0) {
    Serial.read();
  }


  Serial.print("Confirmation: ");


  // ----------------------------------------------------------
  // Wait for NEW confirmation
  // ----------------------------------------------------------

  while (!Serial.available()) {
    delay(10);
  }


  // ----------------------------------------------------------
  // Read until ENTER
  // ----------------------------------------------------------

  String confirmation =
    Serial.readStringUntil('\n');

  confirmation.trim();


  Serial.println(confirmation);


  // ----------------------------------------------------------
  // Verify
  // ----------------------------------------------------------

  if (
    confirmation != "Y" &&
    confirmation != "y"
  ) {

    Serial.println();
    Serial.println("[INFO] Deletion cancelled.");

    showMenu();

    return;
  }


  // ==========================================================
  // DELETE
  // ==========================================================

  uint8_t result = finger.deleteModel(id);


  if (result == FINGERPRINT_OK) {

    Serial.println();
    Serial.println("========================================");
    Serial.println("        FINGERPRINT DELETED");
    Serial.println("========================================");

    Serial.print("Deleted ID: ");
    Serial.println(id);

    showStorageCount();

  } else {

    Serial.println();
    Serial.println("[ERROR] Failed to delete fingerprint.");

    Serial.print("Error code: ");
    Serial.println(result);
  }


  showMenu();
}


// ============================================================
// SEARCH FINGERPRINT
// ============================================================

void searchFingerprint() {

  Serial.println();
  Serial.println("========================================");
  Serial.println("        FINGERPRINT SEARCH");
  Serial.println("========================================");

  Serial.println();
  Serial.println("Place your finger...");


  uint8_t result;


  // ==========================================================
  // WAIT FOR FINGER
  // ==========================================================

  while (true) {

    result = finger.getImage();


    if (result == FINGERPRINT_OK) {

      break;
    }


    if (result != FINGERPRINT_NOFINGER) {

      Serial.print(
        "[ERROR] getImage() code: "
      );

      Serial.println(result);

      showMenu();

      return;
    }


    delay(100);
  }


  Serial.println(
    "[OK] Finger detected."
  );


  // ==========================================================
  // CONVERT FINGERPRINT
  // ==========================================================

  result = finger.image2Tz();


  if (result != FINGERPRINT_OK) {

    Serial.print(
      "[ERROR] Fingerprint conversion failed. Code: "
    );

    Serial.println(result);

    waitForFingerRemoval();

    showMenu();

    return;
  }


  Serial.println(
    "[OK] Fingerprint converted."
  );


  // ==========================================================
  // SEARCH DATABASE
  // ==========================================================

  Serial.println(
    "Searching stored fingerprints..."
  );


  result = finger.fingerFastSearch();


  if (result == FINGERPRINT_OK) {

    Serial.println();
    Serial.println("========================================");
    Serial.println("        FINGERPRINT FOUND");
    Serial.println("========================================");

    Serial.print("Fingerprint ID: ");
    Serial.println(finger.fingerID);

    Serial.print("Confidence: ");
    Serial.println(finger.confidence);

  }

  else if (result == FINGERPRINT_NOTFOUND) {

    Serial.println();
    Serial.println("========================================");
    Serial.println("       FINGERPRINT NOT FOUND");
    Serial.println("========================================");

    Serial.println(
      "This fingerprint is not stored."
    );

  }

  else {

    Serial.println();
    Serial.print(
      "[ERROR] Search failed. Code: "
    );

    Serial.println(result);
  }


  waitForFingerRemoval();

  showMenu();
}


// ============================================================
// STORAGE INFORMATION
// ============================================================

void showStorageInfo() {

  Serial.println();
  Serial.println("========================================");
  Serial.println("         SENSOR INFORMATION");
  Serial.println("========================================");


  finger.getParameters();


  Serial.print("Capacity: ");
  Serial.println(finger.capacity);

  Serial.print("Security level: ");
  Serial.println(finger.security_level);

  Serial.print("Packet length: ");
  Serial.println(finger.packet_len);


  uint8_t result =
    finger.getTemplateCount();


  if (result == FINGERPRINT_OK) {

    Serial.print("Stored fingerprints: ");
    Serial.println(finger.templateCount);

  } else {

    Serial.print(
      "[ERROR] Could not get template count. Code: "
    );

    Serial.println(result);
  }


  showMenu();
}


// ============================================================
// DELETE ALL FINGERPRINTS
// ============================================================

void emptyDatabase() {

  Serial.println();
  Serial.println("========================================");
  Serial.println("            !!! WARNING !!!");
  Serial.println("========================================");

  Serial.println();

  Serial.println(
    "THIS WILL DELETE EVERY FINGERPRINT"
  );

  Serial.println(
    "STORED INSIDE THE AS608."
  );

  Serial.println();

  Serial.println(
    "This includes ALL IDs."
  );

  Serial.println();

  Serial.println(
    "Type DELETE and press Enter to confirm."
  );

  Serial.println(
    "Type anything else to cancel."
  );

  Serial.println();


  // ==========================================================
  // CRITICAL SERIAL FIX
  // ==========================================================
  //
  // The "6" command was followed by ENTER.
  //
  // Depending on the Serial Monitor setting, that ENTER can
  // still be sitting in the Serial buffer.
  //
  // If we don't remove it, the program can immediately think
  // the user has responded to the DELETE confirmation.
  //
  // So we completely clear the old input first.
  //
  // ==========================================================

  while (Serial.available() > 0) {
    Serial.read();
  }


  Serial.print("Confirmation: ");


  // ==========================================================
  // WAIT FOR BRAND NEW INPUT
  // ==========================================================

  while (Serial.available() == 0) {
    delay(10);
  }


  // ==========================================================
  // READ CONFIRMATION
  // ==========================================================

  String confirmation =
    Serial.readStringUntil('\n');

  confirmation.trim();


  Serial.println(confirmation);


  // ==========================================================
  // VERIFY CONFIRMATION
  // ==========================================================

  if (confirmation != "DELETE") {

    Serial.println();
    Serial.println(
      "[INFO] Database wipe cancelled."
    );

    showMenu();

    return;
  }


  // ==========================================================
  // DELETE EVERYTHING
  // ==========================================================

  Serial.println();
  Serial.println(
    "Deleting all fingerprints..."
  );

  Serial.println(
    "Please wait..."
  );


  uint8_t result =
    finger.emptyDatabase();


  // ==========================================================
  // RESULT
  // ==========================================================

  if (result == FINGERPRINT_OK) {

    Serial.println();
    Serial.println("========================================");
    Serial.println("       DATABASE CLEARED");
    Serial.println("========================================");


    // --------------------------------------------------------
    // Verify database is empty
    // --------------------------------------------------------

    if (
      finger.getTemplateCount()
      == FINGERPRINT_OK
    ) {

      Serial.print(
        "Fingerprints remaining: "
      );

      Serial.println(
        finger.templateCount
      );

    } else {

      Serial.println(
        "[WARNING] Could not verify fingerprint count."
      );
    }

  } else {

    Serial.println();
    Serial.println("========================================");
    Serial.println("          DELETE FAILED");
    Serial.println("========================================");

    Serial.print("Error code: ");
    Serial.println(result);
  }


  showMenu();
}


// ============================================================
// WAIT FOR FINGER REMOVAL
// ============================================================

void waitForFingerRemoval() {

  Serial.println();
  Serial.println("Remove your finger...");


  while (
    finger.getImage()
    != FINGERPRINT_NOFINGER
  ) {

    delay(100);
  }


  Serial.println(
    "Finger removed."
  );
}