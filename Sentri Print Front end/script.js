/* =========================================================
   SENTRIPRINT - FRONTEND APPLICATION
   ========================================================= */


/* =========================================================
   CONFIGURATION
   ========================================================= */

const API_BASE_URL = "http://10.189.243.199:8000";

const POLL_INTERVAL = 3000;


/* =========================================================
   APPLICATION STATE
   ========================================================= */

let attendanceRecords = [];

let totalStudents = 0;

let attendanceActive = false;

let lastKnownAttendanceCount = 0;


/* =========================================================
   DOM ELEMENTS
   ========================================================= */

const scannerTitle =
  document.getElementById("scannerTitle");

const scannerMessage =
  document.getElementById("scannerMessage");

const scannerLoader =
  document.getElementById("scannerLoader");

const studentResult =
  document.getElementById("studentResult");

const attendanceList =
  document.getElementById("attendanceList");

const emptyState =
  document.getElementById("emptyState");

const totalStudentsElement =
  document.getElementById("totalStudents");

const presentCountElement =
  document.getElementById("presentCount");

const attendanceRateElement =
  document.getElementById("attendanceRate");

const lastScanElement =
  document.getElementById("lastScan");


/* =========================================================
   ATTENDANCE CONTROL BUTTONS
   ========================================================= */

const startAttendanceBtn =
  document.getElementById(
    "startAttendanceBtn"
  );

const stopAttendanceBtn =
  document.getElementById(
    "stopAttendanceBtn"
  );

const resetAttendanceBtn =
  document.getElementById(
    "resetAttendanceBtn"
  );


/* =========================================================
   CLOCK
   ========================================================= */

function updateClock() {

  const now = new Date();

  const dateElement =
    document.getElementById("currentDate");

  const timeElement =
    document.getElementById("currentTime");


  if (dateElement) {

    const dateOptions = {
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "numeric"
    };

    dateElement.textContent =
      now.toLocaleDateString(
        "en-US",
        dateOptions
      );
  }


  if (timeElement) {

    timeElement.textContent =
      now.toLocaleTimeString(
        "en-US",
        {
          hour12: false
        }
      );
  }
}


setInterval(updateClock, 1000);

updateClock();


/* =========================================================
   API REQUEST HELPER
   ========================================================= */

async function apiRequest(
  endpoint,
  options = {}
) {

  const response =
    await fetch(
      `${API_BASE_URL}${endpoint}`,
      {
        headers: {
          "Content-Type": "application/json"
        },
        ...options
      }
    );


  if (!response.ok) {

    let errorMessage =
      `Request failed with status ${response.status}`;


    try {

      const errorData =
        await response.json();


      if (errorData.detail) {

        errorMessage =
          errorData.detail;
      }

    } catch (error) {

      // Ignore JSON parsing errors.
    }


    const apiError =
      new Error(errorMessage);

    apiError.status =
      response.status;

    throw apiError;
  }


  return response.json();
}


/* =========================================================
   NORMALIZE STUDENT RESPONSE
   ========================================================= */

function normalizeStudents(data) {

  /*
   * The /students endpoint may return:
   *
   * 1. A direct array
   *
   * OR
   *
   * 2. A wrapped response:
   *
   * {
   *   status: "success",
   *   count: 2,
   *   students: [...]
   * }
   */

  if (Array.isArray(data)) {

    return data;
  }


  if (
    data &&
    Array.isArray(data.students)
  ) {

    return data.students;
  }


  console.warn(
    "Unexpected students response:",
    data
  );


  return [];
}


/* =========================================================
   NORMALIZE ATTENDANCE RESPONSE
   ========================================================= */

function normalizeAttendance(data) {

  /*
   * The /attendance/current endpoint returns:
   *
   * {
   *   status: "success",
   *   count: 1,
   *   attendance: [...]
   * }
   */

  if (Array.isArray(data)) {

    return data;
  }


  if (
    data &&
    Array.isArray(data.attendance)
  ) {

    return data.attendance;
  }


  console.warn(
    "Unexpected attendance response:",
    data
  );


  return [];
}


/* =========================================================
   CONNECTION STATUS
   ========================================================= */

function setConnectionStatus(online) {

  const statusDot =
    document.querySelector(".status-dot");

  const statusTitle =
    document.querySelector(
      ".connection-status strong"
    );

  const statusMessage =
    document.querySelector(
      ".connection-status small"
    );


  if (
    !statusDot ||
    !statusTitle ||
    !statusMessage
  ) {

    return;
  }


  if (online) {

    statusDot.style.background =
      "#22c55e";

    statusTitle.textContent =
      "System Online";

    statusMessage.textContent =
      "Fingerprint server connected";

  } else {

    statusDot.style.background =
      "#ef4444";

    statusTitle.textContent =
      "System Offline";

    statusMessage.textContent =
      "Unable to reach fingerprint server";
  }
}


/* =========================================================
   ATTENDANCE CONTROL STATE
   ========================================================= */

function updateAttendanceControls() {

  /*
   * When attendance is active:
   *
   * Start  → disabled
   * Stop   → enabled
   * Reset  → disabled
   *
   * Reset is disabled because the backend
   * intentionally does not allow resetting
   * while an attendance session is running.
   */

  if (startAttendanceBtn) {

    startAttendanceBtn.disabled =
      attendanceActive;
  }


  if (stopAttendanceBtn) {

    stopAttendanceBtn.disabled =
      !attendanceActive;
  }


  if (resetAttendanceBtn) {

    resetAttendanceBtn.disabled =
      attendanceActive;
  }
}


/* =========================================================
   START ATTENDANCE
   ========================================================= */

async function startAttendance() {

  /*
   * Prevent unnecessary API requests
   * if attendance is already active.
   */

  if (attendanceActive) {

    return;
  }


  try {

    console.log(
      "Starting attendance session..."
    );


    /*
     * Tell FastAPI to open a new
     * attendance session.
     */

    await apiRequest(
      "/attendance/start",
      {
        method: "POST"
      }
    );


    /*
     * Update frontend state.
     */

    attendanceActive = true;

    lastKnownAttendanceCount = 0;


    /*
     * A new attendance session starts
     * with an empty visible attendance list.
     *
     * This does NOT delete anything
     * from SQLite.
     */

    attendanceRecords = [];


    /*
     * Clear previous student result.
     */

    if (studentResult) {

      studentResult.classList.add(
        "hidden"
      );
    }


    /*
     * Reset the last scan display.
     */

    if (lastScanElement) {

      lastScanElement.textContent =
        "--:--";
    }


    /*
     * Update the dashboard.
     */

    await renderAttendanceList();

    updateStatistics();

    updateScannerStatus();

    updateAttendanceControls();


    console.log(
      "Attendance session started."
    );


  } catch (error) {

    console.error(
      "Failed to start attendance:",
      error
    );


    alert(
      `Unable to start attendance:\n${error.message}`
    );


    /*
     * Re-check the backend state in case
     * another session is already active.
     */

    await loadAttendanceStatus();
  }
}


/* =========================================================
   STOP ATTENDANCE
   ========================================================= */

async function stopAttendance() {

  /*
   * Nothing to stop if the session
   * is already closed.
   */

  if (!attendanceActive) {

    return;
  }


  /*
   * Ask for confirmation before stopping.
   */

  const confirmed =
    confirm(
      "Stop the current attendance session?"
    );


  if (!confirmed) {

    return;
  }


  try {

    console.log(
      "Stopping attendance session..."
    );


    /*
     * Tell FastAPI to close the session.
     */

    const result =
      await apiRequest(
        "/attendance/stop",
        {
          method: "POST"
        }
      );


    /*
     * Update frontend state.
     */

    attendanceActive = false;


    /*
     * Keep the attendance records
     * visible after stopping.
     *
     * They remain stored in SQLite.
     */

    updateScannerStatus();

    updateAttendanceControls();


    console.log(
      "Attendance session stopped:",
      result
    );


    /*
     * Show a simple confirmation.
     */

    alert(
      `Attendance stopped.\n\nStudents recorded: ${result.total_attendees}`
    );


  } catch (error) {

    console.error(
      "Failed to stop attendance:",
      error
    );


    alert(
      `Unable to stop attendance:\n${error.message}`
    );


    /*
     * Re-check the backend state.
     */

    await loadAttendanceStatus();
  }
}


/* =========================================================
   RESET ATTENDANCE
   ========================================================= */

async function resetAttendance() {

  /*
   * The backend does not allow reset while
   * attendance is active.
   */

  if (attendanceActive) {

    alert(
      "Stop the current attendance session before resetting attendance."
    );

    return;
  }


  /*
   * Reset permanently removes attendance
   * records from SQLite.
   *
   * Students and fingerprint registrations
   * are NOT affected.
   */

  const confirmed =
    confirm(
      "This will permanently delete ALL stored attendance records.\n\n" +
      "Students and fingerprint registrations will NOT be deleted.\n\n" +
      "Do you want to continue?"
    );


  if (!confirmed) {

    return;
  }


  try {

    console.log(
      "Resetting attendance records..."
    );


    /*
     * Delete attendance records
     * through the FastAPI endpoint.
     */

    const result =
      await apiRequest(
        "/attendance/reset",
        {
          method: "DELETE"
        }
      );


    /*
     * Clear frontend attendance state.
     */

    attendanceRecords = [];

    lastKnownAttendanceCount = 0;


    /*
     * Clear student result.
     */

    if (studentResult) {

      studentResult.classList.add(
        "hidden"
      );
    }


    /*
     * Reset last scan.
     */

    if (lastScanElement) {

      lastScanElement.textContent =
        "--:--";
    }


    /*
     * Reset scanner display.
     */

    if (scannerTitle) {

      scannerTitle.textContent =
        "Attendance closed";
    }


    if (scannerMessage) {

      scannerMessage.textContent =
        "Start an attendance session before scanning fingerprints.";
    }


    /*
     * Update dashboard.
     */

    await renderAttendanceList();

    updateStatistics();

    updateAttendanceControls();


    console.log(
      "Attendance reset:",
      result
    );


    alert(
      `Attendance reset successfully.\n\nRecords deleted: ${result.deleted_count}`
    );


  } catch (error) {

    console.error(
      "Failed to reset attendance:",
      error
    );


    alert(
      `Unable to reset attendance:\n${error.message}`
    );
  }
}


/* =========================================================
   ATTENDANCE CONTROL EVENTS
   ========================================================= */

if (startAttendanceBtn) {

  startAttendanceBtn.addEventListener(
    "click",
    startAttendance
  );
}


if (stopAttendanceBtn) {

  stopAttendanceBtn.addEventListener(
    "click",
    stopAttendance
  );
}


if (resetAttendanceBtn) {

  resetAttendanceBtn.addEventListener(
    "click",
    resetAttendance
  );
}


/* =========================================================
   LOAD STUDENTS
   ========================================================= */

async function loadStudents() {

  try {

    const data =
      await apiRequest("/students");


    const students =
      normalizeStudents(data);


    totalStudents =
      students.length;


    if (totalStudentsElement) {

      totalStudentsElement.textContent =
        totalStudents;
    }


    setConnectionStatus(true);


    console.log(
      "Students loaded:",
      totalStudents
    );


  } catch (error) {

    console.error(
      "Failed to load students:",
      error
    );

    setConnectionStatus(false);
  }
}


/* =========================================================
   LOAD ATTENDANCE STATUS
   ========================================================= */

async function loadAttendanceStatus() {

  try {

    const status =
      await apiRequest(
        "/attendance/status"
      );


    /*
     * Backend tells us whether the
     * attendance session is active.
     */

    attendanceActive =
      status.attendance_active;


    updateScannerStatus();

    updateAttendanceControls();

    setConnectionStatus(true);


  } catch (error) {

    console.error(
      "Failed to load attendance status:",
      error
    );

    setConnectionStatus(false);
  }
}


/* =========================================================
   LOAD CURRENT ATTENDANCE
   ========================================================= */

async function loadCurrentAttendance() {

  /*
   * If attendance is closed, there is no need
   * to repeatedly request /attendance/current.
   *
   * The backend intentionally returns HTTP 403
   * when the session is closed.
   */

  if (!attendanceActive) {

    return;
  }


  try {

    const data =
      await apiRequest(
        "/attendance/current"
      );


    const records =
      normalizeAttendance(data);


    /*
     * Detect a newly recorded fingerprint.
     *
     * We compare the current record count
     * against the previous count.
     */

    if (
      records.length >
      lastKnownAttendanceCount
    ) {

      const newestRecord =
        records[records.length - 1];


      console.log(
        "New attendance record detected:",
        newestRecord
      );


      await showStudentFromAttendance(
        newestRecord
      );
    }


    /*
     * Save the latest record count.
     */

    lastKnownAttendanceCount =
      records.length;


    /*
     * Save attendance records
     * in application state.
     */

    attendanceRecords =
      records;


    /*
     * Update visible attendance list.
     */

    await renderAttendanceList();


    /*
     * Update dashboard statistics.
     */

    updateStatistics();


    setConnectionStatus(true);


  } catch (error) {

    console.error(
      "Failed to load current attendance:",
      error
    );
  }
}


/* =========================================================
   UPDATE SCANNER STATUS
   ========================================================= */

function updateScannerStatus() {

  if (
    !scannerTitle ||
    !scannerMessage ||
    !scannerLoader ||
    !studentResult
  ) {

    return;
  }


  if (attendanceActive) {

    scannerTitle.textContent =
      "Ready to scan";

    scannerMessage.textContent =
      "Place your finger on the fingerprint scanner.";

    scannerLoader.classList.remove(
      "hidden"
    );

  } else {

    scannerTitle.textContent =
      "Attendance closed";

    scannerMessage.textContent =
      "Start an attendance session before scanning fingerprints.";

    scannerLoader.classList.add(
      "hidden"
    );

  }
}


/* =========================================================
   SHOW STUDENT AFTER SUCCESSFUL SCAN
   ========================================================= */

async function showStudentFromAttendance(
  attendanceData
) {

  try {

    const data =
      await apiRequest(
        "/students"
      );


    /*
     * Normalize the response before
     * using .find().
     */

    const students =
      normalizeStudents(data);


    const student =
      students.find(
        item =>
          item.student_id ===
          attendanceData.student_id
      );


    if (!student) {

      console.warn(
        "Student not found:",
        attendanceData.student_id
      );

      return;
    }


    showStudent(
      student,
      attendanceData
    );


  } catch (error) {

    console.error(
      "Failed to load student details:",
      error
    );
  }
}


/* =========================================================
   SHOW STUDENT RESULT
   ========================================================= */

function showStudent(
  student,
  attendanceData
) {

  const name =
    student.name ||
    "Unknown Student";


  const initials =
    getInitials(name);


  const studentAvatar =
    document.getElementById(
      "studentAvatar"
    );

  const studentName =
    document.getElementById(
      "studentName"
    );

  const studentDetails =
    document.getElementById(
      "studentDetails"
    );


  if (studentAvatar) {

    studentAvatar.textContent =
      initials;
  }


  if (studentName) {

    studentName.textContent =
      name;
  }


  if (studentDetails) {

    studentDetails.textContent =
      `${student.student_id} • ${student.department || "Student"}`;
  }


  if (studentResult) {

    studentResult.classList.remove(
      "hidden"
    );
  }


  if (scannerTitle) {

    scannerTitle.textContent =
      "Attendance recorded";
  }


  if (scannerMessage) {

    scannerMessage.textContent =
      `${name} has been marked present.`;
  }


  updateLastScan(
    attendanceData.timestamp
  );
}


/* =========================================================
   RENDER ATTENDANCE LIST
   ========================================================= */

async function renderAttendanceList() {

  if (!attendanceList) {

    return;
  }


  /*
   * Remove existing attendance rows
   * before rendering the latest data.
   */

  const existingRows =
    attendanceList.querySelectorAll(
      ".attendance-row"
    );


  existingRows.forEach(
    row => row.remove()
  );


  /*
   * Show empty state when there are
   * no attendance records.
   */

  if (
    attendanceRecords.length === 0
  ) {

    if (emptyState) {

      emptyState.classList.remove(
        "hidden"
      );
    }

    return;
  }


  if (emptyState) {

    emptyState.classList.add(
      "hidden"
    );
  }


  /*
   * Load student information so that
   * the attendance list can display
   * names and departments.
   */

  let students = [];


  try {

    const data =
      await apiRequest(
        "/students"
      );


    students =
      normalizeStudents(data);


  } catch (error) {

    console.error(
      "Failed to load students:",
      error
    );
  }


  /*
   * Newest attendance record appears first.
   */

  const records =
    [...attendanceRecords]
      .reverse();


  records.forEach(
    record => {

      const student =
        students.find(
          item =>
            item.student_id ===
            record.student_id
        );


      addAttendanceRow(
        record,
        student,
        attendanceList
      );
    }
  );
}


/* =========================================================
   ADD ATTENDANCE ROW
   ========================================================= */

function addAttendanceRow(
  record,
  student,
  list
) {

  const row =
    document.createElement(
      "div"
    );


  row.className =
    "attendance-row";


  const name =
    student?.name ||
    record.student_id ||
    "Unknown Student";


  const initials =
    getInitials(name);


  const department =
    student?.department ||
    "Student";


  const time =
    formatTime(
      record.timestamp
    );


  row.innerHTML = `
    <div class="attendance-avatar">
      ${initials}
    </div>

    <div class="attendance-info">
      <strong>${name}</strong>
      <span>${record.student_id} • ${department}</span>
    </div>

    <div class="attendance-time">
      ${time}
    </div>
  `;


  list.appendChild(row);
}


/* =========================================================
   UPDATE STATISTICS
   ========================================================= */

function updateStatistics() {

  const present =
    attendanceRecords.length;


  if (presentCountElement) {

    presentCountElement.textContent =
      present;
  }


  const rate =
    totalStudents > 0
      ? Math.round(
          (present / totalStudents) * 100
        )
      : 0;


  if (attendanceRateElement) {

    attendanceRateElement.textContent =
      `${rate}%`;
  }
}


/* =========================================================
   UPDATE LAST SCAN
   ========================================================= */

function updateLastScan(timestamp) {

  if (
    !timestamp ||
    !lastScanElement
  ) {

    return;
  }


  lastScanElement.textContent =
    formatTime(timestamp);
}


/* =========================================================
   FORMAT TIME
   ========================================================= */

function formatTime(timestamp) {

  const date =
    new Date(timestamp);


  if (
    Number.isNaN(
      date.getTime()
    )
  ) {

    return "--:--";
  }


  return date.toLocaleTimeString(
    "en-US",
    {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true
    }
  );
}


/* =========================================================
   GET INITIALS
   ========================================================= */

function getInitials(name) {

  if (!name) {

    return "SP";
  }


  const parts =
    name
      .trim()
      .split(/\s+/);


  if (parts.length === 1) {

    return parts[0]
      .substring(0, 2)
      .toUpperCase();
  }


  return (
    parts[0][0] +
    parts[parts.length - 1][0]
  ).toUpperCase();
}


/* =========================================================
   INITIALIZE DASHBOARD
   ========================================================= */

async function initializeDashboard() {

  console.log(
    "Initializing SentriPrint dashboard..."
  );


  /*
   * First load the registered students.
   */

  await loadStudents();


  /*
   * Check whether an attendance session
   * is currently active.
   */

  await loadAttendanceStatus();


  /*
   * Only load attendance records when
   * the backend says the session is active.
   */

  await loadCurrentAttendance();


  /*
   * Make sure controls reflect the
   * backend state after initialization.
   */

  updateAttendanceControls();


  console.log(
    "SentriPrint dashboard initialized."
  );
}


/* =========================================================
   REAL-TIME POLLING
   ========================================================= */

setInterval(
  async () => {

    /*
     * Keep the attendance session state
     * synchronized with the backend.
     */

    await loadAttendanceStatus();


    /*
     * If attendance is active, retrieve
     * the latest attendance records.
     */

    await loadCurrentAttendance();

  },
  POLL_INTERVAL
);


/* =========================================================
   START APPLICATION
   ========================================================= */

initializeDashboard();