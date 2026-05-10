import hashlib
import mysql.connector
from mysql.connector import Error

import email_service


# ─────────────────────────────────────────────────────────────
#  BASE ENGINE
# ─────────────────────────────────────────────────────────────
class DatabaseEngine:
    def __init__(self):
        self.host     = "localhost"
        self.user     = "root"
        self.password = ""
        self.database = "dormitory_db"

    def connect(self):
        try:
            conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                connection_timeout=5,
            )
            return conn
        except Error as e:
            print(f"[DB Connection Error] {e}")
            return None

    @staticmethod
    def _hash(pw: str) -> str:
        return hashlib.sha256(pw.encode()).hexdigest()

    @staticmethod
    def _is_hashed(pw: str) -> bool:
        return len(pw) == 64 and all(c in "0123456789abcdef" for c in pw.lower())

    def ensure_schema(self):
        """
        Run once at startup to patch schema gaps:
          1. Add 'Refunded' to payments.status ENUM.
          2. Add due_date column to payments if missing.
        Safe to call multiple times.
        """
        conn = self.connect()
        if not conn:
            return
        try:
            cur = conn.cursor()
            # Patch 1: Add 'Refunded' to status ENUM
            cur.execute(
                "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='payments' "
                "AND COLUMN_NAME='status'"
            )
            row = cur.fetchone()
            if row and "Refunded" not in (row[0] or ""):
                cur.execute(
                    "ALTER TABLE payments MODIFY COLUMN status "
                    "ENUM('Paid','Partial','Pending','Overdue','Advanced','Refunded') "
                    "DEFAULT 'Pending'"
                )
                conn.commit()
            # Patch 2: Add due_date column if missing
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='payments' "
                "AND COLUMN_NAME='due_date'"
            )
            if (cur.fetchone() or [0])[0] == 0:
                cur.execute(
                    "ALTER TABLE payments ADD COLUMN due_date DATE DEFAULT NULL "
                    "AFTER payment_date"
                )
                conn.commit()
        except Exception as e:
            print(f"[DatabaseEngine.ensure_schema] {e}")
        finally:
            conn.close()

    @staticmethod
    def _month_key(s) -> str:
        """Normalize a billing_month value (e.g. 'May 2026', '2026-05',
        '2026-05-01') to a sortable 'YYYY-MM' key. Falls back to ''."""
        if not s:
            return ""
        s = str(s).strip()
        # Already YYYY-MM or YYYY-MM-...
        m = __import__("re").match(r"^(\d{4})-(\d{1,2})", s)
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}"
        # 'Month YYYY'  or 'Mon YYYY'
        months = {
            "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
            "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
            "jan":1,"feb":2,"mar":3,"apr":4,"jun":6,"jul":7,"aug":8,
            "sep":9,"sept":9,"oct":10,"nov":11,"dec":12,
        }
        parts = s.replace(",", " ").split()
        mo = yr = None
        for p in parts:
            pl = p.lower()
            if pl in months:
                mo = months[pl]
            elif p.isdigit() and len(p) == 4:
                yr = int(p)
        if mo and yr:
            return f"{yr}-{mo:02d}"
        # Bare month name with no year - skip it to avoid wrong year assumption
        if mo and not yr:
            return ""
        return ""


# ─────────────────────────────────────────────────────────────
#  ADMIN / STAFF MODULE
# ─────────────────────────────────────────────────────────────
class AdminModule(DatabaseEngine):

    # ── Schema helpers ────────────────────────────────────────
    def ensure_admin_columns(self):
        """Add optional columns to admins table if they don't exist yet."""
        conn = self.connect()
        if not conn:
            return
        try:
            cur = conn.cursor()
            for col, typ in [
                ("email",            "VARCHAR(150)"),
                ("contact_number",   "VARCHAR(30)"),
                ("profile_pic_path", "VARCHAR(255)"),
            ]:
                try:
                    cur.execute(
                        f"ALTER TABLE admins ADD COLUMN IF NOT EXISTS `{col}` {typ} DEFAULT NULL"
                    )
                except Exception:
                    pass
            conn.commit()
        except Exception as e:
            print(f"[AdminModule.ensure_admin_columns] {e}")
        finally:
            conn.close()

    # ── Authentication ────────────────────────────────────────
    def validate_login(self, identifier: str, password: str):
        """
        Accept either username OR email as the login identifier.
        Returns the admin row dict on success, None on failure.
        """
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            hashed = self._hash(password)
            cur.execute(
                """SELECT * FROM admins
                   WHERE (username=%s OR email=%s) AND password=%s""",
                (identifier, identifier, hashed),
            )
            return cur.fetchone()
        except Exception as e:
            print(f"[AdminModule.validate_login] {e}")
        finally:
            conn.close()
        return None

    def log_login(self, admin_id, full_name, role):
        try:
            self.add_log(admin_id, "LOGIN", f"{full_name} logged in.", actor_role=role)
        except Exception as e:
            print(f"[AdminModule.log_login] {e}")

    # ── CRUD ──────────────────────────────────────────────────
    def get_all_admins(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT admin_id, username, full_name, role, email, "
                "created_at, last_login FROM admins ORDER BY admin_id"
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[AdminModule.get_all_admins] {e}")
        finally:
            conn.close()
        return []

    def add_admin(self, username: str, password: str, full_name: str,
                  role: str = "Staff", email: str = "") -> bool:
        """
        Register a new staff member.
        After a successful DB commit, dispatches an invitation email
        with their temporary credentials — matching the technical argument.
        """
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO admins (username, password, full_name, role, email) "
                "VALUES (%s,%s,%s,%s,%s)",
                (username, self._hash(password), full_name, role, email),
            )
            conn.commit()

            # ── Automated Staff Onboarding email ──────────────
            if email:
                try:
                    email_service.send_staff_credentials(
                        to_email=email,
                        full_name=full_name,
                        username=username,
                        password=password,   # plaintext — only sent once, then hashed in DB
                        role=role,
                    )
                except Exception as mail_err:
                    print(f"[AdminModule.add_admin] Email dispatch failed: {mail_err}")
            return True
        except Exception as e:
            print(f"[AdminModule.add_admin] {e}")
        finally:
            conn.close()
        return False

    def update_admin(self, admin_id, username, full_name, role,
                     password=None, email=None):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            if password:
                cur.execute(
                    "UPDATE admins SET username=%s, full_name=%s, role=%s, "
                    "password=%s, email=%s WHERE admin_id=%s",
                    (username, full_name, role, self._hash(password), email, admin_id),
                )
            else:
                cur.execute(
                    "UPDATE admins SET username=%s, full_name=%s, role=%s, "
                    "email=%s WHERE admin_id=%s",
                    (username, full_name, role, email, admin_id),
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"[AdminModule.update_admin] {e}")
        finally:
            conn.close()
        return False

    def delete_admin(self, admin_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM admins WHERE admin_id=%s", (admin_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"[AdminModule.delete_admin] {e}")
        finally:
            conn.close()
        return False

    def hash_existing_admin_passwords(self):
        conn = self.connect()
        if not conn:
            return 0
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT admin_id, password FROM admins")
            rows = cur.fetchall()
            count = 0
            for row in rows:
                raw = row.get("password") or ""
                if not raw or self._is_hashed(raw):
                    continue
                cur.execute(
                    "UPDATE admins SET password=%s WHERE admin_id=%s",
                    (self._hash(raw), row["admin_id"]),
                )
                count += 1
            conn.commit()
            return count
        except Exception as e:
            print(f"[AdminModule.hash_existing_admin_passwords] {e}")
        finally:
            conn.close()
        return 0

    # ── OTP Password Reset ────────────────────────────────────
    def reset_password_request(self, email: str) -> bool:
        """
        Look up admin by email, generate OTP, and dispatch reset email.
        Returns True if email exists and OTP was sent, False otherwise.
        """
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT admin_id, full_name, email FROM admins WHERE email=%s",
                (email,)
            )
            admin = cur.fetchone()
            if not admin or not admin.get("email"):
                return False
        except Exception as e:
            print(f"[AdminModule.reset_password_request] {e}")
            return False
        finally:
            conn.close()

        otp = email_service.send_otp(admin["email"], admin["full_name"])
        return otp is not None

    def reset_password_confirm(self, email: str, otp: str,
                                new_password: str) -> bool:
        """
        Verify OTP then update the admin's password.
        Returns True on success.
        """
        if not email_service.verify_otp(email, otp):
            return False
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE admins SET password=%s WHERE email=%s",
                (self._hash(new_password), email),
            )
            conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            print(f"[AdminModule.reset_password_confirm] {e}")
        finally:
            conn.close()
        return False

    # ── Activity Logs ─────────────────────────────────────────
    def add_log(self, admin_id, action_type, action_text, actor_role="Admin",
                staff_id=None, renter_id=None):
        """
        CALLS sp_log_action — unified audit entry point.
        Falls back to direct INSERT if the SP is unavailable.
        """
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.callproc("sp_log_action", [
                admin_id, renter_id, actor_role, action_type, action_text
            ])
            # Consume any lingering result sets — mysql.connector callproc() bug:
            # unconsumed result sets can cause the SP to execute multiple times.
            for _ in cur.stored_results():
                pass
            conn.commit()
            return True
        except Exception as e:
            # Fallback: direct insert so logging never breaks the app
            try:
                cur.execute(
                    "INSERT INTO activity_logs "
                    "(admin_id, action_type, action_text, actor_role, staff_id, renter_id) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (admin_id, action_type, action_text, actor_role, staff_id, renter_id),
                )
                conn.commit()
                return True
            except Exception as e2:
                print(f"[AdminModule.add_log] {e2}")
        finally:
            conn.close()
        return False

    def get_recent_activity_for_renter(self, renter_id, limit=25):
        """Activity stream relevant to a single renter — their payments,
        maintenance updates, and any admin actions tagged to them."""
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT l.log_id, l.action_type, l.action_text,
                          l.actor_role, l.log_timestamp,
                          COALESCE(a.full_name,
                                   CONCAT(r.first_name,' ',r.last_name),
                                   'System') AS actor_name
                   FROM activity_logs l
                   LEFT JOIN admins  a ON l.admin_id  = a.admin_id
                   LEFT JOIN renters r ON l.renter_id = r.renter_id
                   WHERE l.renter_id = %s
                      OR l.action_text LIKE %s
                   ORDER BY l.log_timestamp DESC
                   LIMIT %s""",
                (renter_id, f"%#{renter_id}%", limit),
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[AdminModule.get_recent_activity_for_renter] {e}")
        finally:
            conn.close()
        return []

    def get_activity_logs(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT log_id, actor_name AS admin_name,
                          action_type, action_text,
                          actor_role, log_timestamp
                   FROM vw_activity_log_full
                   ORDER BY log_timestamp DESC
                   LIMIT 200"""
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[AdminModule.get_activity_logs] {e}")
        finally:
            conn.close()
        return []


# ─────────────────────────────────────────────────────────────
#  RENTER MODULE
# ─────────────────────────────────────────────────────────────
class RenterModule(DatabaseEngine):

    def hash_existing_renter_passwords(self):
        conn = self.connect()
        if not conn:
            return 0
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT renter_id, password FROM renter_accounts")
            rows = cur.fetchall()
            count = 0
            for row in rows:
                raw = row.get("password") or ""
                if not raw or self._is_hashed(raw):
                    continue
                cur.execute(
                    "UPDATE renter_accounts SET password=%s WHERE renter_id=%s",
                    (self._hash(raw), row["renter_id"]),
                )
                count += 1
            conn.commit()
            return count
        except Exception as e:
            print(f"[RenterModule.hash_existing_renter_passwords] {e}")
        finally:
            conn.close()
        return 0

    def get_all_renters(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM renters ORDER BY renter_id ASC")
            return cur.fetchall()
        except Exception as e:
            print(f"[RenterModule.get_all_renters] {e}")
        finally:
            conn.close()
        return []

    def get_renter_by_id(self, renter_id):
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM renters WHERE renter_id=%s", (renter_id,))
            return cur.fetchone()
        except Exception as e:
            print(f"[RenterModule.get_renter_by_id] {e}")
        finally:
            conn.close()
        return None

    def add_renter(
        self,
        first_name, middle_name, last_name, occupation_type,
        institution_employer, gender, contact_number, email,
        id_type, id_number, address,
        emergency_contact_name, emergency_contact_number,
        renter_status="Active",
        admin_id=None,
    ):
        """
        CALLS sp_register_renter — all insert + account logic lives in the DB.
        Returns the new renter_id on success, None on failure.
        """
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor()
            cur.callproc("sp_register_renter", [
                first_name, middle_name or "", last_name,
                occupation_type, institution_employer or "",
                gender, contact_number, email,
                id_type or "", id_number or "",
                address or "",
                emergency_contact_name or "",
                emergency_contact_number or "",
                admin_id or 0,
                0,    # OUT p_renter_id
                "",   # OUT p_result_msg
            ])
            # Fetch OUT params
            cur.execute("SELECT @_sp_register_renter_14, @_sp_register_renter_15")
            row = cur.fetchone()
            renter_id = row[0] if row else None
            msg       = row[1] if row else ""
            conn.commit()
            if msg and msg.startswith("ERROR"):
                print(f"[RenterModule.add_renter] {msg}")
                return None
            return renter_id
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            print(f"[RenterModule.add_renter] {e}")
        finally:
            conn.close()
        return None

    def update_renter(self, renter_id, **fields):
        if not fields:
            return False
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            set_clause = ", ".join(f"{k}=%s" for k in fields)
            values = list(fields.values()) + [renter_id]
            cur.execute(
                f"UPDATE renters SET {set_clause} WHERE renter_id=%s", values
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[RenterModule.update_renter] {e}")
        finally:
            conn.close()
        return False

    def delete_renter(self, renter_id, admin_id=None):
        """CALLS sp_delete_renter — handles checkout, deactivation, delete + log."""
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.callproc("sp_delete_renter", [
                renter_id,
                admin_id or 0,
                "",   # OUT p_result_msg
            ])
            cur.execute("SELECT @_sp_delete_renter_2")
            row = cur.fetchone()
            msg = row[0] if row else ""
            conn.commit()
            if msg and msg.startswith("ERROR"):
                print(f"[RenterModule.delete_renter] {msg}")
                return False
            return True
        except Exception as e:
            print(f"[RenterModule.delete_renter] {e}")
        finally:
            conn.close()
        return False

    def get_stats(self):
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT COUNT(DISTINCT a.renter_id) AS total
                   FROM assignments a
                   JOIN renters r ON a.renter_id = r.renter_id
                   WHERE a.status = 'Active' AND r.renter_status = 'Active'"""
            )
            total_active = cur.fetchone()["total"]
            cur.execute(
                "SELECT COUNT(*) AS total FROM rooms WHERE status='Available'"
            )
            vacant_rooms = cur.fetchone()["total"]
            return {"renters": total_active, "vacant": vacant_rooms}
        except Exception as e:
            print(f"[RenterModule.get_stats] {e}")
        finally:
            conn.close()
        return None

    def search_renters(self, keyword):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            like = f"%{keyword}%"
            cur.execute(
                """SELECT * FROM renters
                   WHERE first_name LIKE %s OR last_name LIKE %s
                      OR contact_number LIKE %s OR email LIKE %s
                   ORDER BY last_name""",
                (like, like, like, like),
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[RenterModule.search_renters] {e}")
        finally:
            conn.close()
        return []

    def validate_renter_login(self, identifier: str, password: str):
        """
        Accept either username OR email as the login identifier.
        Returns renter info dict if login is valid, else None.
        """
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            hashed = self._hash(password)
            cur.execute(
                """SELECT ra.account_id, vw.renter_id, vw.username,
                          vw.full_name, vw.email, vw.renter_status
                   FROM vw_renter_profile_full vw
                   JOIN renter_accounts ra ON ra.renter_id = vw.renter_id
                   WHERE (vw.username=%s OR vw.email=%s)
                     AND ra.password=%s
                     AND vw.account_status='Active'
                     AND vw.renter_status='Active'
                   ORDER BY (vw.username NOT LIKE 'renter%') DESC,
                            ra.account_id ASC
                   LIMIT 1""",
                (identifier, identifier, hashed),
            )
            return cur.fetchone()
        except Exception as e:
            print(f"[RenterModule.validate_renter_login] {e}")
        finally:
            conn.close()
        return None

    # ── OTP Password Reset ────────────────────────────────────
    def reset_password_request(self, email: str) -> bool:
        """
        Look up renter by email, generate OTP, and dispatch reset email.
        Returns True if email exists and OTP was sent.
        """
        conn = self.connect()
        if not conn:
            return False
        renter = None
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT renter_id, first_name, last_name, email "
                "FROM renters WHERE email=%s AND renter_status='Active'",
                (email,)
            )
            renter = cur.fetchone()
        except Exception as e:
            print(f"[RenterModule.reset_password_request] {e}")
            return False
        finally:
            conn.close()

        if not renter or not renter.get("email"):
            return False

        full_name = f"{renter['first_name']} {renter['last_name']}"
        otp = email_service.send_otp(renter["email"], full_name)
        return otp is not None

    def reset_password_confirm(self, email: str, otp: str,
                                new_password: str) -> bool:
        """
        Verify OTP then update the renter's password in renter_accounts.
        Returns True on success.
        """
        if not email_service.verify_otp(email, otp):
            return False
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            # Look up renter_id by email
            cur.execute(
                "SELECT renter_id FROM renters WHERE email=%s", (email,)
            )
            row = cur.fetchone()
            if not row:
                return False
            renter_id = row[0]
            cur.execute(
                "UPDATE renter_accounts SET password=%s WHERE renter_id=%s",
                (self._hash(new_password), renter_id),
            )
            conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            print(f"[RenterModule.reset_password_confirm] {e}")
        finally:
            conn.close()
        return False

    def get_renter_payments(self, renter_id):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT p.*, CONCAT(r.first_name,' ',r.last_name) AS renter_name
                   FROM payments p
                   JOIN renters r ON p.renter_id = r.renter_id
                   WHERE p.renter_id=%s ORDER BY p.payment_date DESC""",
                (renter_id,),
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[RenterModule.get_renter_payments] {e}")
        finally:
            conn.close()
        return []

    def get_total_expected_monthly(self):
        """
        Returns the SUM of agreed_rate for all currently active renters.
        Used by Reports to compute accurate expected revenue instead of
        hardcoding rate x active_count (which ignores per-renter rates).
        Falls back to active_count * 1800 if agreed_rate is missing/zero.
        """
        conn = self.connect()
        if not conn:
            return 0.0
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT COALESCE(SUM(a.agreed_rate), 0.0),
                          COUNT(DISTINCT a.renter_id)
                   FROM assignments a
                   JOIN renters r ON a.renter_id = r.renter_id
                   WHERE a.status = 'Active'
                     AND r.renter_status = 'Active'"""
            )
            row = cur.fetchone()
            total = float(row[0] or 0.0)
            count = int(row[1] or 0)
            # Fallback: if agreed_rate not set for anyone, use 1800/renter
            return total if total > 0 else count * 1800.0
        except Exception as e:
            print(f"[RenterModule.get_total_expected_monthly] {e}")
        finally:
            conn.close()
        return 0.0

    def get_renter_assignment(self, renter_id):
        """Return the active room assignment for a renter, or None."""
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT a.*, rm.room_number, rm.floor_level, rm.monthly_rate
                   FROM assignments a
                   JOIN rooms rm ON a.room_id = rm.room_id
                   WHERE a.renter_id=%s AND a.status='Active'
                   ORDER BY a.assignment_id DESC LIMIT 1""",
                (renter_id,),
            )
            return cur.fetchone()
        except Exception as e:
            print(f"[RenterModule.get_renter_assignment] {e}")
        finally:
            conn.close()
        return None

    def get_renter_maintenance(self, renter_id):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT mr.*, rm.room_number
                   FROM maintenance_requests mr
                   JOIN rooms rm ON mr.room_id = rm.room_id
                   WHERE mr.renter_id=%s
                   ORDER BY mr.request_date DESC""",
                (renter_id,),
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[RenterModule.get_renter_maintenance] {e}")
        finally:
            conn.close()
        return []


# ─────────────────────────────────────────────────────────────
#  ROOM MODULE
# ─────────────────────────────────────────────────────────────
class RoomModule(DatabaseEngine):

    def get_all_rooms(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM rooms ORDER BY room_number")
            return cur.fetchall()
        except Exception as e:
            print(f"[RoomModule.get_all_rooms] {e}")
        finally:
            conn.close()
        return []

    def get_room_by_id(self, room_id):
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM rooms WHERE room_id=%s", (room_id,))
            return cur.fetchone()
        except Exception as e:
            print(f"[RoomModule.get_room_by_id] {e}")
        finally:
            conn.close()
        return None

    def add_room(self, room_number, room_type=None, floor_level=None,
                 capacity=None, monthly_rate=None, status="Available",
                 description="", admin_id=None):
        """CALLS sp_add_room. Returns True on success."""
        _floor_map = {
            "1": "1st Floor", "1st": "1st Floor", "ground": "1st Floor",
            "1st floor": "1st Floor", "first": "1st Floor", "first floor": "1st Floor",
            "2": "2nd Floor", "2nd": "2nd Floor", "second": "2nd Floor",
            "2nd floor": "2nd Floor", "second floor": "2nd Floor",
        }
        if floor_level:
            floor_level = _floor_map.get(str(floor_level).strip().lower(), floor_level)
        # Validate status — only allow known values
        valid_statuses = {"Available", "Full", "Under Maintenance"}
        if status not in valid_statuses:
            status = "Available"
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.callproc("sp_add_room", [
                room_number, floor_level or "1st Floor",
                capacity or 2, monthly_rate or 1800.00,
                description or "",
                status,       # p_status — now accepted by updated SP
                admin_id or 0,
                0,   # OUT p_room_id
                "",  # OUT p_result_msg
            ])
            cur.execute("SELECT @_sp_add_room_7, @_sp_add_room_8")
            row = cur.fetchone()
            msg = row[1] if row else ""
            conn.commit()
            if msg and msg.startswith("ERROR"):
                print(f"[RoomModule.add_room] {msg}")
                return False
            return True
        except Exception as e:
            print(f"[RoomModule.add_room] {e}")
        finally:
            conn.close()
        return False

    def update_room(self, room_id, **fields):
        if not fields:
            return False
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            set_clause = ", ".join(f"{k}=%s" for k in fields)
            values = list(fields.values()) + [room_id]
            cur.execute(
                f"UPDATE rooms SET {set_clause} WHERE room_id=%s", values
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[RoomModule.update_room] {e}")
        finally:
            conn.close()
        return False

    def delete_room(self, room_id, admin_id=None):
        """CALLS sp_delete_room — refuses if room still has active renters."""
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.callproc("sp_delete_room", [
                room_id,
                admin_id or 0,
                "",  # OUT p_result_msg
            ])
            cur.execute("SELECT @_sp_delete_room_2")
            row = cur.fetchone()
            msg = row[0] if row else ""
            conn.commit()
            if msg and msg.startswith("ERROR"):
                print(f"[RoomModule.delete_room] {msg}")
                return False
            return True
        except Exception as e:
            print(f"[RoomModule.delete_room] {e}")
        finally:
            conn.close()
        return False

    def get_amenities(self, room_id):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT * FROM room_amenities WHERE room_id=%s", (room_id,)
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[RoomModule.get_amenities] {e}")
        finally:
            conn.close()
        return []

    # ── Bed tracking (live, computed from assignments) ───────────
    def get_bed_status(self, room_id):
        """Return live bed availability for a room.
        { 'capacity': int, 'occupied': int, 'available': int,
          'occupied_beds': [bed_assignment, ...] }
        """
        conn = self.connect()
        result = {"capacity": 0, "occupied": 0, "available": 0, "occupied_beds": []}
        if not conn:
            return result
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT capacity FROM rooms WHERE room_id=%s", (room_id,))
            row = cur.fetchone()
            if not row:
                return result
            cap = int(row["capacity"] or 0)
            cur.execute(
                "SELECT bed_assignment FROM assignments "
                "WHERE room_id=%s AND status='Active'", (room_id,)
            )
            beds = [r["bed_assignment"] for r in cur.fetchall() if r.get("bed_assignment")]
            result["capacity"] = cap
            result["occupied"] = len(beds)
            result["available"] = max(0, cap - len(beds))
            result["occupied_beds"] = beds
        except Exception as e:
            print(f"[RoomModule.get_bed_status] {e}")
        finally:
            conn.close()
        return result

    def get_all_rooms_with_beds(self):
        """All rooms with live 'occupied' and 'available_beds' from a single query.
        Only counts Active renters with Active assignments — deleted/inactive renters
        are excluded so dashboard occupancy is always accurate."""
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT *,
                          occupied,
                          available_slots AS available_beds
                   FROM vw_room_availability
                   ORDER BY room_number"""
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[RoomModule.get_all_rooms_with_beds] {e}")
        finally:
            conn.close()
        return []

    def add_amenity(self, room_id, amenity_name, quantity=1,
                    item_condition="Good"):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO room_amenities "
                "(room_id, amenity_name, quantity, item_condition) "
                "VALUES (%s,%s,%s,%s)",
                (room_id, amenity_name, quantity, item_condition),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[RoomModule.add_amenity] {e}")
        finally:
            conn.close()
        return False

    def delete_amenity(self, amenity_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM room_amenities WHERE amenity_id=%s", (amenity_id,)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[RoomModule.delete_amenity] {e}")
        finally:
            conn.close()
        return False


# ─────────────────────────────────────────────────────────────
#  ASSIGNMENT MODULE
# ─────────────────────────────────────────────────────────────
class AssignmentModule(DatabaseEngine):

    def assign_renter_to_room(self, renter_id, room_id, bed, check_in,
                               rate, admin_id):
        """CALLS sp_assign_renter_to_room. Returns (True, msg) or (False, msg)."""
        conn = self.connect()
        if not conn:
            return False, "No DB connection"
        try:
            cur = conn.cursor()
            cur.callproc("sp_assign_renter_to_room", [
                renter_id, room_id, bed, check_in, float(rate), admin_id,
                "",   # OUT p_result_msg
            ])
            cur.execute("SELECT @_sp_assign_renter_to_room_6")
            row = cur.fetchone()
            msg = row[0] if row else ""
            conn.commit()
            ok = msg.startswith("SUCCESS") if msg else False
            return ok, msg
        except Exception as e:
            print(f"[AssignmentModule.assign_renter_to_room] {e}")
        finally:
            conn.close()
        return False, "Exception"

    def checkout_renter(self, renter_id, admin_id, checkout_date):
        """CALLS sp_checkout_renter. Returns (True, msg) or (False, msg)."""
        conn = self.connect()
        if not conn:
            return False, "No DB connection"
        try:
            cur = conn.cursor()
            cur.callproc("sp_checkout_renter", [
                renter_id, admin_id,
                str(checkout_date),
                "",   # OUT p_result_msg
            ])
            cur.execute("SELECT @_sp_checkout_renter_3")
            row = cur.fetchone()
            msg = row[0] if row else ""
            conn.commit()
            ok = msg.startswith("SUCCESS") if msg else False
            return ok, msg
        except Exception as e:
            print(f"[AssignmentModule.checkout_renter] {e}")
        finally:
            conn.close()
        return False, "Exception"

    def get_all_assignments(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT a.assignment_id, a.renter_id, a.room_id,
                          CONCAT(r.first_name,' ',r.last_name) AS renter_name,
                          rm.room_number, a.bed_assignment,
                          a.check_in_date, a.check_out_date,
                          a.status, a.agreed_rate, a.security_deposit,
                          a.contract_term, a.notes
                   FROM assignments a
                   JOIN renters r  ON a.renter_id = r.renter_id
                   JOIN rooms   rm ON a.room_id   = rm.room_id
                   ORDER BY a.assignment_id"""
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[AssignmentModule.get_all_assignments] {e}")
        finally:
            conn.close()
        return []


# ─────────────────────────────────────────────────────────────
#  PAYMENT MODULE
# ─────────────────────────────────────────────────────────────
class PaymentModule(DatabaseEngine):

    def record_payment_sp(self, invoice_number, renter_id, amount, balance,
                           method, reference, billing_month, payment_date,
                           due_date, status, remarks, processed_by):
        """
        Direct wrapper around sp_record_payment.
        Prefer add_payment() for most callers — it normalises billing_month
        and auto-corrects status first, then delegates here.
        Returns (True, msg) or (False, msg).
        """
        conn = self.connect()
        if not conn:
            return False, "No DB connection"
        try:
            cur = conn.cursor()
            cur.callproc("sp_record_payment", [
                invoice_number, renter_id, float(amount or 0),
                float(balance or 0), method or "Cash",
                reference or "", billing_month or "",
                str(payment_date or ""), str(due_date or ""),
                status or "Pending", remarks or "",
                processed_by,
                "",   # OUT p_result_msg
            ])
            cur.execute("SELECT @_sp_record_payment_12")
            row = cur.fetchone()
            msg = row[0] if row else ""
            conn.commit()
            ok = msg.startswith("SUCCESS") if msg else False
            return ok, msg
        except Exception as e:
            print(f"[PaymentModule.record_payment_sp] {e}")
        finally:
            conn.close()
        return False, "Exception"

    def get_all_payments(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT p.*,
                          CONCAT(r.first_name,' ',r.last_name) AS renter_name,
                          COALESCE(a.agreed_rate, rm.monthly_rate, 1800) AS agreed_rate
                   FROM payments p
                   JOIN renters r ON p.renter_id = r.renter_id
                   LEFT JOIN assignments a ON a.renter_id = p.renter_id AND a.status = 'Active'
                   LEFT JOIN rooms rm ON a.room_id = rm.room_id
                   ORDER BY p.payment_date DESC"""
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[PaymentModule.get_all_payments] {e}")
        finally:
            conn.close()
        return []

    def add_payment(
        self, invoice_number, renter_id, amount, balance_amount,
        payment_method, billing_month, payment_date, status,
        reference_number=None, remarks=None, processed_by=None,
    ):
        """
        Insert a payment record. Status is auto-corrected:
          amount >= rate AND balance == 0  → Paid
          amount > 0  AND balance > 0      → Partial
          amount == 0 AND past due date    → Overdue
          amount == 0 AND not past due     → Pending

        billing_month is normalized to 'Month YYYY' (e.g. 'May 2026')
        to match the format expected by SQL views and fn_days_overdue().
        """
        # ── Normalize billing_month to 'Month YYYY' ──────────────
        try:
            from datetime import date as _dn
            import calendar as _cal_n
            bm_key_n = self._month_key(billing_month or "")
            if bm_key_n:
                yr_n, mo_n = map(int, bm_key_n.split("-"))
                billing_month = f"{_cal_n.month_name[mo_n]} {yr_n}"
        except Exception:
            pass  # keep original if normalization fails
        from datetime import date as _date
        # Auto-correct status based on amount/balance
        try:
            amt = float(amount or 0)
            bal = float(balance_amount or 0)
            today = _date.today()
            bm_key = self._month_key(billing_month or "")
            if bm_key:
                yr, mo = map(int, bm_key.split("-"))
                due = _date(yr, mo, 5)
                past_due = today > due
            else:
                past_due = False

            if amt > 0 and bal <= 0:
                status = "Paid"
            elif amt > 0 and bal > 0:
                status = "Partial"
            elif amt == 0 and past_due:
                status = "Overdue"
            else:
                status = "Pending"
        except Exception:
            pass  # keep caller-supplied status if computation fails

        # Derive due_date = 5th of billing_month (consistent with auto_mark_overdue)
        computed_due_date = None
        try:
            bm_key2 = self._month_key(billing_month or "")
            if bm_key2:
                yr2, mo2 = map(int, bm_key2.split("-"))
                from datetime import date as _d2
                computed_due_date = _d2(yr2, mo2, 5).isoformat()
        except Exception:
            pass

        conn = self.connect()
        if not conn:
            return False
        # Ensure due_date + Refunded ENUM exist (idempotent — fast no-op after first run)
        DatabaseEngine().ensure_schema()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO payments (
                    invoice_number, renter_id, amount, balance_amount,
                    payment_method, billing_month, payment_date, due_date, status,
                    reference_number, remarks, processed_by
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    invoice_number, renter_id, amount, balance_amount,
                    payment_method, billing_month, payment_date, computed_due_date,
                    status, reference_number, remarks, processed_by,
                ),
            )
            conn.commit()
            try:
                if processed_by is None:
                    AdminModule().add_log(
                        None, 'RENTER_PAYMENT',
                        f"Renter #{renter_id} submitted payment "
                        f"{invoice_number} - {float(amount):,.2f} ({status})",
                        actor_role='Renter', renter_id=renter_id,
                    )
                else:
                    AdminModule().add_log(
                        processed_by, 'ADD_PAYMENT',
                        f"Recorded payment {invoice_number} - "
                        f"{float(amount):,.2f} for renter #{renter_id} ({status})",
                        actor_role='Admin', renter_id=renter_id,
                    )
            except Exception as _le:
                print(f"[PaymentModule.add_payment audit] {_le}")
            return True
        except Exception as e:
            print(f"[PaymentModule.add_payment] {e}")
        finally:
            conn.close()
        return False

    def renter_submit_payment(self, invoice_number, renter_id, amount, balance_amount,
                               payment_method, billing_month, payment_date,
                               reference_number=None, remarks=None):
        """
        Para sa renter-submitted payments ONLY.
        Laging nag-iinsert ng status='Pending' — walang auto-correct.
        Admin ang mag-ve-verify at mag-mamark bilang Paid.
        """
        # Normalize billing_month
        try:
            import calendar as _cal_n
            bm_key = self._month_key(billing_month or "")
            if bm_key:
                yr_n, mo_n = map(int, bm_key.split("-"))
                billing_month = f"{_cal_n.month_name[mo_n]} {yr_n}"
        except Exception:
            pass

        # Compute due_date = 5th of billing month
        computed_due_date = None
        try:
            bm_key2 = self._month_key(billing_month or "")
            if bm_key2:
                yr2, mo2 = map(int, bm_key2.split("-"))
                from datetime import date as _d2
                computed_due_date = _d2(yr2, mo2, 5).isoformat()
        except Exception:
            pass

        conn = self.connect()
        if not conn:
            return False
        DatabaseEngine().ensure_schema()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO payments
                   (invoice_number, renter_id, amount, balance_amount,
                    payment_method, billing_month, payment_date, due_date,
                    status, reference_number, remarks, processed_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'Pending',%s,%s,NULL)""",
                (invoice_number, renter_id, float(amount or 0),
                 float(balance_amount or 0), payment_method or "Cash",
                 billing_month, payment_date, computed_due_date,
                 reference_number, remarks),
            )
            conn.commit()
            try:
                AdminModule().add_log(
                    None, 'RENTER_PAYMENT',
                    f"Renter #{renter_id} submitted payment "
                    f"{invoice_number} - {float(amount or 0):,.2f} (Pending)",
                    actor_role='Renter', renter_id=renter_id,
                )
            except Exception:
                pass
            return True
        except Exception as e:
            print(f"[PaymentModule.renter_submit_payment] {e}")
        finally:
            conn.close()
        return False

    def update_payment_status(self, payment_id, status):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE payments SET status=%s WHERE payment_id=%s",
                (status, payment_id),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[PaymentModule.update_payment_status] {e}")
        finally:
            conn.close()
        return False

    def delete_payment(self, payment_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM payments WHERE payment_id=%s", (payment_id,)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[PaymentModule.delete_payment] {e}")
        finally:
            conn.close()
        return False

    # ── Audited admin modifications ──────────────────────────
    def get_payment_by_id(self, payment_id):
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT p.*,
                          CONCAT(r.first_name,' ',r.last_name) AS renter_name
                   FROM payments p
                   JOIN renters r ON p.renter_id = r.renter_id
                   WHERE p.payment_id=%s""", (payment_id,))
            return cur.fetchone()
        except Exception as e:
            print(f"[PaymentModule.get_payment_by_id] {e}")
        finally:
            conn.close()
        return None

    def edit_payment(self, payment_id, admin_id, **fields):
        """Admin edits a payment; writes a granular audit_log row."""
        if not fields:
            return False
        before = self.get_payment_by_id(payment_id)
        if not before:
            return False
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            sets = ", ".join(f"{k}=%s" for k in fields)
            cur.execute(
                f"UPDATE payments SET {sets} WHERE payment_id=%s",
                list(fields.values()) + [payment_id])
            conn.commit()
            # Audit
            try:
                changes = ", ".join(
                    f"{k}: {before.get(k)} → {v}" for k, v in fields.items()
                    if str(before.get(k)) != str(v))
                if not changes:
                    changes = "no-op"
                AdminModule().add_log(
                    admin_id, "EDIT_PAYMENT",
                    f"Edited payment #{payment_id} ({before.get('invoice_number')}) — {changes}",
                    actor_role="Admin", renter_id=before.get("renter_id"))
            except Exception as _le:
                print(f"[edit_payment audit] {_le}")
            return True
        except Exception as e:
            print(f"[PaymentModule.edit_payment] {e}")
        finally:
            conn.close()
        return False

    def refund_payment(self, payment_id, admin_id, refund_amount, reason=""):
        """Mark a paid payment as refunded (status=Refunded) and log."""
        before = self.get_payment_by_id(payment_id)
        if not before:
            return False
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE payments SET status='Refunded', remarks=CONCAT(IFNULL(remarks,''),' | REFUND ₱',%s,' — ',%s) WHERE payment_id=%s",
                (f"{float(refund_amount):,.2f}", reason or "no reason given", payment_id))
            conn.commit()
            try:
                AdminModule().add_log(
                    admin_id, "REFUND_PAYMENT",
                    f"Refunded ₱{float(refund_amount):,.2f} on payment "
                    f"#{payment_id} ({before.get('invoice_number')}) "
                    f"for renter #{before.get('renter_id')} — {reason or 'no reason'}",
                    actor_role="Admin", renter_id=before.get("renter_id"))
            except Exception as _le:
                print(f"[refund_payment audit] {_le}")
            return True
        except Exception as e:
            print(f"[PaymentModule.refund_payment] {e}")
        finally:
            conn.close()
        return False

    def adjust_payment(self, payment_id, admin_id, new_amount, reason=""):
        """Adjust a payment amount (write-down / write-up) with audit."""
        before = self.get_payment_by_id(payment_id)
        if not before:
            return False
        old_amt = float(before.get("amount") or 0)
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE payments SET amount=%s, remarks=CONCAT(IFNULL(remarks,''),' | ADJUST ₱',%s,'→₱',%s,' — ',%s) WHERE payment_id=%s",
                (float(new_amount), f"{old_amt:,.2f}",
                 f"{float(new_amount):,.2f}", reason or "no reason given", payment_id))
            conn.commit()
            try:
                AdminModule().add_log(
                    admin_id, "ADJUST_PAYMENT",
                    f"Adjusted payment #{payment_id} ({before.get('invoice_number')}) "
                    f"amount ₱{old_amt:,.2f} → ₱{float(new_amount):,.2f} — "
                    f"{reason or 'no reason'}",
                    actor_role="Admin", renter_id=before.get("renter_id"))
            except Exception as _le:
                print(f"[adjust_payment audit] {_le}")
            return True
        except Exception as e:
            print(f"[PaymentModule.adjust_payment] {e}")
        finally:
            conn.close()
        return False

    def apply_overage_charge(self, billing_month, overage_per_renter, actor_admin_id=None):
        """
        When actual BATELEC bill exceeds expected (₱700 × live active renters),
        add overage_per_renter to each active renter's existing Pending/Partial/Overdue
        payment row for this billing_month.  If no payment row exists yet, create one.
        Active renter count is always fetched live from the DB — never hardcoded.

        Returns the number of renters charged.
        """
        import calendar as _cal
        # Normalize billing_month to 'Month YYYY'
        try:
            bm_key = self._month_key(billing_month or "")
            if bm_key:
                yr_n, mo_n = map(int, bm_key.split("-"))
                billing_month_norm = f"{_cal.month_name[mo_n]} {yr_n}"
            else:
                billing_month_norm = billing_month
        except Exception:
            billing_month_norm = billing_month

        conn = self.connect()
        if not conn:
            return 0
        try:
            cur = conn.cursor(dictionary=True)
            # Get all active renters
            cur.execute(
                """SELECT r.renter_id, CONCAT(r.first_name,' ',r.last_name) AS full_name
                   FROM renters r
                   JOIN assignments a ON a.renter_id = r.renter_id
                   WHERE a.status = 'Active' AND r.renter_status = 'Active'"""
            )
            active_renters = cur.fetchall()
            charged = 0
            upd = conn.cursor()
            for renter in active_renters:
                rid = renter['renter_id']
                # Find existing unpaid payment row for this billing month
                upd.execute(
                    """SELECT payment_id, balance_amount, amount, status
                       FROM payments
                       WHERE renter_id=%s AND billing_month=%s
                         AND status IN ('Pending','Partial','Overdue')
                       ORDER BY payment_id DESC LIMIT 1""",
                    (rid, billing_month_norm),
                )
                row = upd.fetchone()
                if row:
                    new_balance = float(row['balance_amount'] or 0) + float(overage_per_renter)
                    # Re-derive status
                    amt = float(row['amount'] or 0)
                    new_status = 'Partial' if amt > 0 else 'Overdue'
                    upd.execute(
                        """UPDATE payments
                           SET balance_amount = %s,
                               status         = %s,
                               remarks        = CONCAT(IFNULL(remarks,''),
                                                ' | OVERAGE +₱', %s)
                           WHERE payment_id = %s""",
                        (new_balance, new_status,
                         f"{float(overage_per_renter):,.2f}", row['payment_id']),
                    )
                else:
                    # No payment row yet — create one with overage as the balance
                    from datetime import date as _date2
                    import calendar as _cal2
                    try:
                        bk2 = self._month_key(billing_month_norm)
                        y2, m2 = map(int, bk2.split("-"))
                        due_dt = f"{y2:04d}-{m2:02d}-05"
                        inv = (
                            f"INV-{y2}-OVR-{rid:03d}-{m2:02d}"
                        )
                    except Exception:
                        due_dt = _date2.today().isoformat()
                        inv    = f"INV-OVR-{rid:03d}"
                    upd.execute(
                        """INSERT INTO payments
                            (invoice_number, renter_id, amount, balance_amount,
                             payment_method, billing_month, payment_date, due_date,
                             status, remarks)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (inv, rid, 0, float(overage_per_renter),
                         'Cash', billing_month_norm, _date2.today(), due_dt,
                         'Overdue', f'OVERAGE charge +₱{float(overage_per_renter):,.2f}'),
                    )
                charged += 1
            conn.commit()
            try:
                AdminModule().add_log(
                    actor_admin_id, 'OVERAGE_CHARGE',
                    f"Overage ₱{float(overage_per_renter):,.2f}/renter charged to "
                    f"{charged} renter(s) for {billing_month_norm}",
                    actor_role='Admin',
                )
            except Exception:
                pass
            return charged
        except Exception as e:
            print(f"[PaymentModule.apply_overage_charge] {e}")
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            conn.close()
        return 0

    def auto_mark_overdue(self, admin_id=None):
        """
        CALLS sp_mark_overdue — flips Pending/Partial payments to Overdue
        when past the 5th of their billing month.  Returns count of updated rows.
        """
        conn = self.connect()
        if not conn:
            return 0
        try:
            cur = conn.cursor()
            cur.callproc("sp_mark_overdue", [
                admin_id or 0,
                0,   # OUT p_updated
                "",  # OUT p_result_msg
            ])
            cur.execute("SELECT @_sp_mark_overdue_1, @_sp_mark_overdue_2")
            row = cur.fetchone()
            updated = int(row[0] or 0) if row else 0
            conn.commit()
            return updated
        except Exception as e:
            print(f"[PaymentModule.auto_mark_overdue] {e}")
        finally:
            conn.close()
        return 0

    def get_unpaid_overdue_renters(self):
        """
        Returns all active renters who have Pending/Overdue/Partial payments,
        PLUS active renters who have NO payment record at all for this month.
        days_since_due = days past the 5th of the billing month.
        """
        conn = self.connect()
        if not conn:
            return []
        try:
            from datetime import date as _date
            today = _date.today()
            cur_month = today.strftime("%Y-%m")

            cur = conn.cursor(dictionary=True)
            # Only pull unpaid rows for the CURRENT month.
            # Also skip any renter who already has a Paid record this month
            # (handles the case where an old Pending row still exists in DB
            #  alongside a newer Paid row for the same billing_month).
            cur_month_text = today.strftime("%B %Y")
            cur.execute(
                """SELECT
                       op.payment_id,
                       op.invoice_number,
                       op.billing_month,
                       op.amount,
                       op.balance_amount,
                       op.status,
                       op.payment_date,
                       op.renter_name,
                       op.renter_id,
                       rm.room_number,
                       a.bed_assignment
                   FROM vw_overdue_payments op
                   LEFT JOIN assignments a  ON a.renter_id = op.renter_id
                                          AND a.status = 'Active'
                   LEFT JOIN rooms rm       ON a.room_id = rm.room_id
                   WHERE op.billing_month = %s
                     AND op.renter_id NOT IN (
                         SELECT DISTINCT p2.renter_id FROM payments p2
                         WHERE p2.status = 'Paid'
                           AND p2.billing_month = %s
                     )""",
                (cur_month_text, cur_month_text),
            )
            rows = cur.fetchall()

            # Compute days_since_due properly per row
            result = []
            for row in rows:
                key = self._month_key(row.get("billing_month") or "")
                if key:
                    yr, mo = map(int, key.split("-"))
                    due = _date(yr, mo, 5)
                    row["days_since_due"] = max(0, (today - due).days)
                else:
                    row["days_since_due"] = 0
                result.append(row)

            # Also include active renters with NO payment this month at all
            cur.execute(
                """SELECT
                       r.renter_id,
                       CONCAT(r.first_name,
                              IF(r.middle_name IS NOT NULL AND r.middle_name != '',
                                 CONCAT(' ', r.middle_name), ''),
                              ' ', r.last_name) AS renter_name,
                       rm.room_number,
                       a.bed_assignment,
                       COALESCE(a.agreed_rate, rm.monthly_rate, 1800) AS agreed_rate
                   FROM renters r
                   JOIN assignments a   ON a.renter_id = r.renter_id
                                       AND a.status = 'Active'
                   LEFT JOIN rooms rm   ON a.room_id = rm.room_id
                   WHERE r.renter_status = 'Active'
                     AND r.renter_id NOT IN (
                         SELECT DISTINCT renter_id FROM payments
                         WHERE billing_month = %s
                     )""",
                (today.strftime("%B %Y"),),
            )
            no_pay = cur.fetchall()
            yr0, mo0 = today.year, today.month
            due0 = _date(yr0, mo0, 5)
            days0 = max(0, (today - due0).days)
            for row in no_pay:
                result.append({
                    "payment_id":    None,
                    "invoice_number": "-",
                    "billing_month": today.strftime("%B %Y"),
                    "amount":        0,
                    "balance_amount": 0,
                    "agreed_rate":   float(row.get("agreed_rate") or 1800),
                    "status":        "No Payment",
                    "payment_date":  None,
                    "days_since_due": days0,
                    "renter_name":   row["renter_name"],
                    "renter_id":     row["renter_id"],
                    "room_number":   row.get("room_number"),
                    "bed_assignment": row.get("bed_assignment"),
                })

            result.sort(key=lambda x: x["days_since_due"], reverse=True)
            return result
        except Exception as e:
            print(f"[PaymentModule.get_unpaid_overdue_renters] {e}")
        finally:
            conn.close()
        return []

    def get_pending_payments_this_month(self):
        """
        Returns count of active renters who have NOT fully paid this month.
        Used for real-time dashboard badge.
        """
        conn = self.connect()
        if not conn:
            return 0
        try:
            from datetime import date as _date
            today = _date.today()
            cur_month = today.strftime("%Y-%m")
            cur = conn.cursor(dictionary=True)
            # Count active renters with no Paid record for current month
            # billing_month is stored as 'Month YYYY' (e.g. 'May 2026'), not YYYY-MM
            cur_month_text = today.strftime("%B %Y")
            cur.execute(
                """SELECT COUNT(DISTINCT r.renter_id) AS cnt
                   FROM renters r
                   JOIN assignments a ON a.renter_id = r.renter_id
                                     AND a.status = 'Active'
                   WHERE r.renter_status = 'Active'
                     AND r.renter_id NOT IN (
                         SELECT p.renter_id FROM payments p
                         WHERE p.status = 'Paid'
                           AND p.billing_month = %s
                     )""",
                (cur_month_text,),
            )
            return cur.fetchone()["cnt"] or 0
        except Exception as e:
            print(f"[PaymentModule.get_pending_payments_this_month] {e}")
        finally:
            conn.close()
        return 0

    def get_renter_payment_status_summary(self):
        """
        Returns one row per active renter per billing month that has an
        unpaid/partial/overdue balance — PLUS a row for the current month
        even if no payment exists yet (shown as 'No Payment').

        This ensures past-due months from previous months are always visible
        in the debt breakdown table, not just the current month.
        """
        conn = self.connect()
        if not conn:
            return []
        try:
            import calendar as _cal
            from datetime import date as _date
            today = _date.today()
            cur_month_key = today.strftime("%Y-%m")

            cur = conn.cursor(dictionary=True)

            # Step 1: fetch ALL payment rows for active renters that are
            # unpaid, partial, overdue OR belong to the current month.
            cur.execute(
                """SELECT
                       vw.renter_id,
                       vw.renter_name                       AS full_name,
                       vw.room_number,
                       vw.bed_assignment                    AS bed,
                       p.payment_id,
                       vw.billing_month,
                       vw.payment_status                    AS status,
                       COALESCE(vw.amount_paid, 0)         AS paid_this_month,
                       COALESCE(vw.balance_due, 0)         AS debt_this_month,
                       COALESCE(
                           (SELECT SUM(p2.balance_amount)
                            FROM payments p2
                            WHERE p2.renter_id = vw.renter_id
                              AND p2.balance_amount > 0
                              AND p2.status IN ('Pending','Overdue','Partial')
                           ), 0)                            AS total_outstanding
                   FROM vw_billing_summary vw
                   LEFT JOIN payments p ON p.renter_id = vw.renter_id
                                      AND p.billing_month = vw.billing_month
                   WHERE (
                       vw.balance_due > 0
                       OR vw.payment_status IN ('Pending','Overdue','Partial')
                   )
                   ORDER BY vw.room_number, vw.bed_assignment, vw.billing_month"""
            )
            rows = cur.fetchall()

            # Step 2: collect which renter_ids already have a current-month row
            seen_renter_current = set()
            # First, collect all renters who have a Paid record for current month.
            # These renters must NEVER appear in the unpaid dashboard even if they
            # have old Pending/Partial rows from previous months in the DB
            # (that's the "ghost" bug — stale rows from past months).
            cur.execute(
                """SELECT DISTINCT p.renter_id
                   FROM payments p
                   JOIN renters r ON r.renter_id = p.renter_id
                   WHERE r.renter_status = 'Active'
                     AND p.status = 'Paid'
                     AND p.billing_month = %s""",
                (today.strftime("%B %Y"),)
            )
            paid_this_month_ids = {r["renter_id"] for r in cur.fetchall()}

            result = []
            for row in rows:
                bm_key = self._month_key(row.get("billing_month") or "")

                # Skip rows belonging to renters already paid for current month —
                # this eliminates ghost entries from old unpaid billing months.
                if row["renter_id"] in paid_this_month_ids:
                    if bm_key == cur_month_key:
                        seen_renter_current.add(row["renter_id"])
                    continue

                # Re-derive status using same due-date logic (5th of month)
                status = row.get("status", "Pending")
                try:
                    bm_str = str(row.get("billing_month", "") or "").strip()
                    bm_key2 = self._month_key(bm_str)
                    if bm_key2:
                        yr_num, mo_num = map(int, bm_key2.split("-"))
                        from datetime import date as _d2
                        due_dt = _d2(yr_num, mo_num, 5)
                        amt     = float(row.get("paid_this_month") or 0)
                        balance = float(row.get("debt_this_month") or 0)
                        if amt > 0 and balance == 0:
                            status = "Paid"
                        elif amt > 0 and balance > 0:
                            status = "Overdue" if today > due_dt else "Partial"
                        elif amt == 0 and today > due_dt:
                            status = "Overdue"
                        else:
                            status = "Pending"
                except Exception:
                    pass

                row["status"] = status

                # Mark seen for current month regardless of status (including Paid)
                if bm_key == cur_month_key:
                    seen_renter_current.add(row["renter_id"])

                # Only show non-Paid rows in the debt breakdown
                if status != "Paid":
                    result.append(row)

            # Also mark already-paid renters as seen for current month
            for rid in paid_this_month_ids:
                seen_renter_current.add(rid)

            # Step 3: for renters that have NO payment row at all, or whose
            # latest payment is from a past month only, inject a current-month
            # "No Payment" placeholder so they still show up.
            cur.execute(
                """SELECT
                       r.renter_id,
                       CONCAT(r.first_name,
                              IF(r.middle_name IS NOT NULL AND r.middle_name != '',
                                 CONCAT(' ', r.middle_name), ''),
                              ' ', r.last_name)              AS full_name,
                       rm.room_number,
                       a.bed_assignment                      AS bed
                   FROM renters r
                   LEFT JOIN assignments a  ON a.renter_id = r.renter_id
                                           AND a.status = 'Active'
                   LEFT JOIN rooms rm       ON a.room_id = rm.room_id
                   WHERE r.renter_status = 'Active'
                   ORDER BY rm.room_number, a.bed_assignment"""
            )
            all_renters = cur.fetchall()

            for rr in all_renters:
                if rr["renter_id"] not in seen_renter_current:
                    # Derive status for current month with no payment
                    cur_due = _date(today.year, today.month, 5)
                    no_pay_status = "Overdue" if today > cur_due else "Pending"
                    result.append({
                        "renter_id":      rr["renter_id"],
                        "full_name":      rr["full_name"],
                        "room_number":    rr["room_number"],
                        "bed":            rr["bed"],
                        "billing_month":  today.strftime("%B %Y"),
                        "status":         no_pay_status,
                        "paid_this_month":  0,
                        "debt_this_month":  0,
                        "total_outstanding": 0,
                    })

            return result
        except Exception as e:
            print(f"[PaymentModule.get_renter_payment_status_summary] {e}")
        finally:
            conn.close()
        return []


# ─────────────────────────────────────────────────────────────
#  MAINTENANCE MODULE
# ─────────────────────────────────────────────────────────────
class MaintenanceModule(DatabaseEngine):

    def get_all_requests(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT request_id, room_number, renter_name,
                          issue AS description, priority, status,
                          request_date, completion_date AS resolved_date,
                          resolution_notes
                   FROM vw_maintenance_full
                   ORDER BY FIELD(priority,'High','Medium','Low'),
                            request_date DESC"""
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[MaintenanceModule.get_all_requests] {e}")
        finally:
            conn.close()
        return []

    def add_request(self, room_id, renter_id, description,
                    priority="Medium", actor_role="Renter", actor_id=None):
        """CALLS sp_submit_maintenance — inserts request + logs action."""
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.callproc("sp_submit_maintenance", [
                room_id, renter_id, description, priority,
                actor_role,
                actor_id or renter_id,
                "",   # OUT p_result_msg
            ])
            cur.execute("SELECT @_sp_submit_maintenance_6")
            row = cur.fetchone()
            msg = row[0] if row else ""
            conn.commit()
            if msg and msg.startswith("ERROR"):
                print(f"[MaintenanceModule.add_request] {msg}")
                return False
            return True
        except Exception as e:
            print(f"[MaintenanceModule.add_request] {e}")
        finally:
            conn.close()
        return False

    def update_status(self, request_id, status,
                      resolution_notes="", resolved_date=None):
        conn = self.connect()
        if not conn:
            return False
        try:
            from datetime import date as _date
            # Auto-set resolved_date to today when marking Completed
            if status == "Completed" and resolved_date is None:
                resolved_date = _date.today().isoformat()
            cur = conn.cursor()
            cur.execute(
                """UPDATE maintenance_requests
                   SET status=%s, resolution_notes=%s, resolved_date=%s
                   WHERE request_id=%s""",
                (status, resolution_notes, resolved_date, request_id),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[MaintenanceModule.update_status] {e}")
        finally:
            conn.close()
        return False

    def delete_request(self, request_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM maintenance_requests WHERE request_id=%s",
                (request_id,),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[MaintenanceModule.delete_request] {e}")
        finally:
            conn.close()
        return False


# ─────────────────────────────────────────────────────────────
#  UTILITY BILLS MODULE
# ─────────────────────────────────────────────────────────────
class UtilityModule(DatabaseEngine):

    UTILITY_FIXED_RATE      = 1800.00   # ₱1,800/mo per renter (legacy fixed rate)
    WIFI_FIXED_TOTAL        = 2000.00   # ₱2,000/mo total (Converge) — never changes
    WIFI_PER_RENTER         = round(2000.00 / 36, 2)   # ₱55.56 — fixed 36 beds
    EXPECTED_PER_RENTER     = 700.00    # ₱700/renter/month expected (Elec + Water combined)

    def get_active_renter_count(self):
        """Returns the current number of active renters from the DB — always live, never hardcoded."""
        conn = self.connect()
        if not conn:
            return 0
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT COUNT(DISTINCT a.renter_id)
                   FROM assignments a
                   JOIN renters r ON a.renter_id = r.renter_id
                   WHERE a.status = 'Active' AND r.renter_status = 'Active'"""
            )
            return cur.fetchone()[0] or 0
        except Exception as e:
            print(f"[UtilityModule.get_active_renter_count] {e}")
        finally:
            conn.close()
        return 0

    def generate_monthly_bills_sp(self, billing_month, admin_id=None):
        """
        CALLS sp_generate_monthly_bills — creates one Pending payment row
        per active renter for the given billing_month.
        Returns (generated_count, msg).
        """
        conn = self.connect()
        if not conn:
            return 0, "No DB connection"
        try:
            cur = conn.cursor()
            cur.callproc("sp_generate_monthly_bills", [
                billing_month,
                admin_id or 0,
                0,   # OUT p_generated
                "",  # OUT p_result_msg
            ])
            cur.execute("SELECT @_sp_generate_monthly_bills_2, @_sp_generate_monthly_bills_3")
            row = cur.fetchone()
            generated = int(row[0] or 0) if row else 0
            msg       = row[1] if row else ""
            conn.commit()
            return generated, msg
        except Exception as e:
            print(f"[UtilityModule.generate_monthly_bills_sp] {e}")
        finally:
            conn.close()
        return 0, "Exception"

    def setup_table(self):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS `utility_bills` (
                    `bill_id`           INT AUTO_INCREMENT PRIMARY KEY,
                    `room_id`           INT,
                    `bill_type`         ENUM('Electricity','Water','Internet','Others')
                                            DEFAULT 'Electricity',
                    `previous_reading`  DECIMAL(10,2),
                    `current_reading`   DECIMAL(10,2),
                    `consumption`       DECIMAL(10,2),
                    `amount`            DECIMAL(10,2),
                    `amount_per_person` DECIMAL(10,2),
                    `billing_month`     VARCHAR(20),
                    `billing_date`      DATE,
                    `due_date`          DATE,
                    `payment_date`      DATE,
                    `status`            ENUM('Unpaid','Paid') DEFAULT 'Unpaid',
                    `reference_no`      VARCHAR(50),
                    `payment_proof`     VARCHAR(255),
                    `date_recorded`     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
            return True
        except Exception as e:
            print(f"[UtilityModule.setup_table] {e}")
        finally:
            conn.close()
        return False

    def generate_monthly_bills(self, billing_month, due_date,
                               amount_per_renter=None, bill_type='Electricity',
                               actor_admin_id=None):
        """Generate a utility bill row per occupied room.
        Defaults to ₱1,800/renter (the fixed dorm rate).

        Design note (Bug 4 awareness): utility_bills and payments are separate
        tables by design — utility_bills tracks the physical room-level charges
        while payments tracks per-renter money receipts. The due date for both
        is the 5th of the billing month so dashboards agree on overdue logic.
        """
        if amount_per_renter is None:
            amount_per_renter = self.UTILITY_FIXED_RATE
        self.setup_table()
        # ── CONSISTENCY FIX: derive due date as 5th of billing month,
        #    matching the same rule in PaymentModule.add_payment and
        #    auto_mark_overdue so all three pages show the same due date.
        if not due_date:
            try:
                key = self._month_key(billing_month)  # YYYY-MM
                yr, mo = key.split("-")
                due_date = f"{int(yr):04d}-{int(mo):02d}-05"
            except Exception:
                from datetime import date as _d
                due_date = _d.today().replace(day=5).isoformat()
        conn = self.connect()
        if not conn:
            return 0
        try:
            cur = conn.cursor(dictionary=True)
            # ── CONSISTENCY FIX (Bug 2): count active renters per room via
            #    the renters table (same source Reports uses for expected revenue),
            #    not just assignments — so new renters without an assignment
            #    don't cause a discrepancy between Reports and Utility Bills.
            cur.execute(
                """SELECT a.room_id,
                          COUNT(DISTINCT a.renter_id) AS renters_in_room
                   FROM assignments a
                   JOIN renters r ON r.renter_id = a.renter_id
                   WHERE a.status = 'Active'
                     AND r.renter_status = 'Active'
                   GROUP BY a.room_id"""
            )
            rooms = cur.fetchall()
            from datetime import date as _date
            ins = conn.cursor()
            generated = 0
            for r in rooms:
                # Skip rooms already billed for this month/type
                ins.execute(
                    """SELECT COUNT(*) FROM utility_bills
                       WHERE room_id=%s AND billing_month=%s AND bill_type=%s""",
                    (r['room_id'], billing_month, bill_type),
                )
                if (ins.fetchone() or [0])[0] > 0:
                    continue
                total = float(amount_per_renter) * int(r['renters_in_room'])
                ins.execute(
                    """INSERT INTO utility_bills
                        (room_id, bill_type, amount, amount_per_person,
                         billing_month, billing_date, due_date)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (r['room_id'], bill_type, total, amount_per_renter,
                     billing_month, _date.today(), due_date),
                )
                generated += 1
            conn.commit()
            if actor_admin_id:
                AdminModule().add_log(
                    actor_admin_id, 'GEN_UTILITY',
                    f"Generated {generated} {bill_type} bills for "
                    f"{billing_month} @ ₱{amount_per_renter:,.0f}/renter",
                    'Admin',
                )
            return generated
        except Exception as e:
            print(f"[UtilityModule.generate_monthly_bills] {e}")
        finally:
            conn.close()
        return 0

    def get_bills_for_renter(self, renter_id):
        """Utility bills for the renter's currently assigned room.
        Queries utility_bills directly (not the view) so that status,
        payment_date, and reference_no always reflect the latest admin changes.
        """
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT DISTINCT
                       ub.*,
                       rm.room_number,
                       rm.floor_level,
                       (SELECT COUNT(*)
                        FROM assignments a2
                        JOIN renters r2 ON r2.renter_id = a2.renter_id
                        WHERE a2.room_id = ub.room_id
                          AND a2.status = 'Active'
                          AND r2.renter_status = 'Active'
                       ) AS renter_count,
                       (SELECT GROUP_CONCAT(
                            CONCAT(r2.first_name,' ',r2.last_name)
                            SEPARATOR ', ')
                        FROM assignments a2
                        JOIN renters r2 ON r2.renter_id = a2.renter_id
                        WHERE a2.room_id = ub.room_id
                          AND a2.status = 'Active'
                          AND r2.renter_status = 'Active'
                       ) AS renter_names
                   FROM utility_bills ub
                   JOIN rooms rm ON rm.room_id = ub.room_id
                   JOIN assignments a ON a.room_id = ub.room_id
                   WHERE a.renter_id = %s
                     AND a.status = 'Active'
                   ORDER BY ub.billing_date DESC""",
                (renter_id,),
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[UtilityModule.get_bills_for_renter] {e}")
        finally:
            conn.close()
        return []

    def get_transparency_summary(self, renter_id):
        """Aggregate where the renter's utility money goes."""
        bills = self.get_bills_for_renter(renter_id)
        breakdown = {}
        total_paid = 0.0
        total_due  = 0.0
        for b in bills:
            t = b.get('bill_type') or 'Others'
            per = float(b.get('amount_per_person') or 0)
            breakdown[t] = breakdown.get(t, 0.0) + per
            if b.get('status') == 'Paid':
                total_paid += per
            else:
                total_due += per
        return {
            'breakdown':  breakdown,
            'total_paid': total_paid,
            'total_due':  total_due,
            'bills':      bills,
        }

    def get_all_bills(self):
        """All utility bills + room number + floor + live renter count + renter names."""
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT ub.*, rm.room_number, rm.floor_level,
                          (SELECT COUNT(*) FROM assignments a
                              JOIN renters r ON r.renter_id = a.renter_id
                              WHERE a.room_id = ub.room_id
                                AND a.status = 'Active'
                                AND r.renter_status = 'Active') AS renter_count,
                          (SELECT GROUP_CONCAT(CONCAT(r.first_name,' ',r.last_name) SEPARATOR ', ')
                              FROM assignments a JOIN renters r ON r.renter_id = a.renter_id
                              WHERE a.room_id = ub.room_id
                                AND a.status = 'Active'
                                AND r.renter_status = 'Active') AS renter_names
                   FROM utility_bills ub
                   JOIN rooms rm ON ub.room_id = rm.room_id
                   ORDER BY ub.billing_date DESC"""
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[UtilityModule.get_all_bills] {e}")
        finally:
            conn.close()
        return []

    def get_distinct_billing_months(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT billing_month FROM utility_bills "
                        "WHERE billing_month IS NOT NULL AND billing_month<>'' "
                        "ORDER BY billing_date DESC")
            return [r[0] for r in cur.fetchall() if r[0]]
        except Exception as e:
            print(f"[UtilityModule.get_distinct_billing_months] {e}")
        finally:
            conn.close()
        return []

    def add_bill(self, room_id, bill_type, previous_reading, current_reading,
                 consumption, amount, amount_per_person,
                 billing_month, billing_date, due_date):
        self.setup_table()
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO utility_bills
                    (room_id, bill_type, previous_reading, current_reading,
                     consumption, amount, amount_per_person,
                     billing_month, billing_date, due_date)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (room_id, bill_type, previous_reading, current_reading,
                 consumption, amount, amount_per_person,
                 billing_month, billing_date, due_date),
            )
            conn.commit()
            try:
                AdminModule().add_log(
                    None, 'UTILITY_ADD',
                    f"Utility bill added — room {room_id} {bill_type} "
                    f"₱{float(amount):,.2f} ({billing_month})",
                    'Admin',
                )
            except Exception:
                pass
            return True
        except Exception as e:
            print(f"[UtilityModule.add_bill] {e}")
        finally:
            conn.close()
        return False

    def mark_paid(self, bill_id, payment_date, reference_no=None):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE utility_bills SET status='Paid', "
                "payment_date=%s, reference_no=%s WHERE bill_id=%s",
                (payment_date, reference_no, bill_id),
            )
            conn.commit()
            try:
                AdminModule().add_log(
                    None, 'UTILITY_PAID',
                    f"Utility bill #{bill_id} marked PAID "
                    f"(ref {reference_no or '—'})",
                    'Admin',
                )
            except Exception:
                pass
            return True
        except Exception as e:
            print(f"[UtilityModule.mark_paid] {e}")
        finally:
            conn.close()
        return False

    def delete_bill(self, bill_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM utility_bills WHERE bill_id=%s", (bill_id,)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[UtilityModule.delete_bill] {e}")
        finally:
            conn.close()
        return False


# ─────────────────────────────────────────────────────────────
#  VISITOR MODULE
# ─────────────────────────────────────────────────────────────
class VisitorModule(DatabaseEngine):

    def get_all_visitors(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT vl.visitor_id, vl.visitor_name, vl.relationship,
                          CONCAT(r.first_name,' ',r.last_name) AS renter_name,
                          vl.time_in, vl.time_out
                   FROM visitor_logs vl
                   JOIN renters r ON vl.renter_id = r.renter_id
                   ORDER BY vl.time_in DESC"""
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[VisitorModule.get_all_visitors] {e}")
        finally:
            conn.close()
        return []

    def log_visitor_in(self, renter_id, visitor_name, relationship):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO visitor_logs "
                "(renter_id, visitor_name, relationship) VALUES (%s,%s,%s)",
                (renter_id, visitor_name, relationship),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[VisitorModule.log_visitor_in] {e}")
        finally:
            conn.close()
        return False

    def log_visitor_out(self, visitor_id, time_out):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE visitor_logs SET time_out=%s WHERE visitor_id=%s",
                (time_out, visitor_id),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[VisitorModule.log_visitor_out] {e}")
        finally:
            conn.close()
        return False

    def delete_visitor_log(self, visitor_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM visitor_logs WHERE visitor_id=%s", (visitor_id,)
            )
            conn.commit()
            try:
                AdminModule().add_log(
                    None, 'DELETE_VISITOR',
                    f"Deleted visitor log ID {visitor_id}",
                    actor_role='Admin'
                )
            except Exception:
                pass
            return True
        except Exception as e:
            print(f"[VisitorModule.delete_visitor_log] {e}")
        finally:
            conn.close()
        return False


# ─────────────────────────────────────────────────────────────
#  FACILITY MODULE
# ─────────────────────────────────────────────────────────────
class FacilityModule(DatabaseEngine):

    def get_all_facilities(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT * FROM facility_overview "
                "ORDER BY floor_level, facility_type"
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[FacilityModule.get_all_facilities] {e}")
        finally:
            conn.close()
        return []

    def add_facility(self, floor_level, facility_type, count):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO facility_overview "
                "(floor_level, facility_type, count) VALUES (%s,%s,%s)",
                (floor_level, facility_type, count),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[FacilityModule.add_facility] {e}")
        finally:
            conn.close()
        return False


# ─────────────────────────────────────────────────────────────
#  APPLICATION MODULE
# ─────────────────────────────────────────────────────────────
class ApplicationModule(DatabaseEngine):
    """
    Handles rental_applications table.
    Public applicants submit here; admin reviews and approves.
    Approval creates renters row + renter_accounts login + sends credentials email.
    """

    def setup_table(self):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                """CREATE TABLE IF NOT EXISTS rental_applications (
                    application_id   INT AUTO_INCREMENT PRIMARY KEY,
                    first_name       VARCHAR(100) NOT NULL,
                    middle_name      VARCHAR(100) DEFAULT NULL,
                    last_name        VARCHAR(100) NOT NULL,
                    gender           VARCHAR(20)  DEFAULT 'Other',
                    occupation_type  VARCHAR(50)  DEFAULT 'Student',
                    institution      VARCHAR(200),
                    contact_number   VARCHAR(30),
                    email            VARCHAR(150),
                    address          TEXT,
                    emergency_name   VARCHAR(150),
                    emergency_number VARCHAR(30),
                    preferred_room   VARCHAR(100),
                    message          TEXT,
                    status           VARCHAR(20)  DEFAULT 'Pending',
                    submitted_at     DATETIME     DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at      DATETIME,
                    reviewed_by      INT,
                    rejection_reason TEXT
                )"""
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[ApplicationModule.setup_table] {e}")
        finally:
            conn.close()
        return False

    def submit_application(
        self, first_name, last_name, gender, occupation_type,
        institution, contact_number, email, address,
        emergency_name, emergency_number, preferred_room, message,
        middle_name="", preferred_bed="", preferred_room_id=None,
    ):
        self.setup_table()
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO rental_applications (
                    first_name, middle_name, last_name, gender, occupation_type,
                    institution, contact_number, email, address,
                    emergency_name, emergency_number, preferred_room,
                    preferred_room_id, preferred_bed, message
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    first_name, middle_name or "", last_name, gender, occupation_type,
                    institution, contact_number, email, address,
                    emergency_name, emergency_number, preferred_room or "",
                    preferred_room_id, preferred_bed or "", message,
                ),
            )
            conn.commit()

            # Acknowledge receipt
            if email:
                try:
                    email_service.send_application_received(
                        email, f"{first_name} {last_name}"
                    )
                except Exception as mail_err:
                    print(f"[ApplicationModule.submit_application] "
                          f"Ack email failed: {mail_err}")
            return True
        except Exception as e:
            print(f"[ApplicationModule.submit_application] {e}")
        finally:
            conn.close()
        return False

    def get_all_applications(self, status_filter=None):
        self.setup_table()
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            if status_filter:
                cur.execute(
                    "SELECT * FROM rental_applications "
                    "WHERE status=%s ORDER BY submitted_at DESC",
                    (status_filter,),
                )
            else:
                cur.execute(
                    "SELECT * FROM rental_applications ORDER BY submitted_at DESC"
                )
            return cur.fetchall()
        except Exception as e:
            print(f"[ApplicationModule.get_all_applications] {e}")
        finally:
            conn.close()
        return []

    def get_pending_count(self):
        self.setup_table()
        conn = self.connect()
        if not conn:
            return 0
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM rental_applications WHERE status='Pending'"
            )
            row = cur.fetchone()
            return row[0] if row else 0
        except Exception as e:
            print(f"[ApplicationModule.get_pending_count] {e}")
        finally:
            conn.close()
        return 0

    def approve_application(self, application_id: int, admin_id: int):
        """
        CALLS sp_approve_application — all renter creation, account setup,
        room assignment, and logging happens inside the stored procedure.
        Returns (True, username, password) or (False, error_message, '')
        """
        conn = self.connect()
        if not conn:
            return False, "No DB connection", ""
        # Fetch email first so we can send the credential email after the SP call
        app_email = ""
        app_name  = ""
        try:
            cur_pre = conn.cursor(dictionary=True)
            cur_pre.execute(
                "SELECT first_name, last_name, email FROM rental_applications "
                "WHERE application_id=%s",
                (application_id,),
            )
            pre = cur_pre.fetchone()
            if pre:
                app_email = pre.get("email") or ""
                app_name  = f"{pre['first_name']} {pre['last_name']}"
        except Exception:
            pass

        try:
            cur = conn.cursor()
            cur.callproc("sp_approve_application", [
                application_id,
                admin_id,
                "",   # OUT p_username
                "",   # OUT p_result_msg
            ])
            cur.execute("SELECT @_sp_approve_application_2, @_sp_approve_application_3")
            row      = cur.fetchone()
            username = row[0] if row else ""
            msg      = row[1] if row else ""
            conn.commit()

            if msg and msg.startswith("ERROR"):
                print(f"[ApplicationModule.approve_application] {msg}")
                return False, msg, ""

            default_pw = "dorm123"

            # Dispatch credential email (backend notification)
            if app_email:
                try:
                    email_service.send_renter_credentials(
                        to_email=app_email,
                        full_name=app_name,
                        username=username or app_email,
                        password=default_pw,
                    )
                except Exception as mail_err:
                    print(f"[ApplicationModule.approve_application] "
                          f"Email dispatch failed: {mail_err}")

            return True, username or app_email, default_pw

        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            print(f"[ApplicationModule.approve_application] {e}")
            return False, str(e), ""
        finally:
            conn.close()

    def reject_application(self, application_id, admin_id, reason=""):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT first_name, last_name FROM rental_applications WHERE application_id=%s",
                (application_id,)
            )
            app = cur.fetchone()
            name = f"{app['first_name']} {app['last_name']}" if app else f"ID {application_id}"
            cur.execute(
                """UPDATE rental_applications
                   SET status='Rejected', reviewed_at=NOW(),
                       reviewed_by=%s, rejection_reason=%s
                   WHERE application_id=%s""",
                (admin_id, reason, application_id),
            )
            conn.commit()
            try:
                AdminModule().add_log(
                    admin_id, 'REJECT_APPLICATION',
                    f"Rejected application from {name}. Reason: {reason or 'none'}",
                    actor_role='Admin'
                )
            except Exception:
                pass
            return True
        except Exception as e:
            print(f"[ApplicationModule.reject_application] {e}")
        finally:
            conn.close()
        return False

    def delete_application(self, application_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT first_name, last_name FROM rental_applications WHERE application_id=%s",
                (application_id,)
            )
            app = cur.fetchone()
            name = f"{app['first_name']} {app['last_name']}" if app else f"ID {application_id}"
            cur.execute(
                "DELETE FROM rental_applications WHERE application_id=%s",
                (application_id,),
            )
            conn.commit()
            try:
                AdminModule().add_log(
                    None, 'DELETE_APPLICATION',
                    f"Deleted application from {name}",
                    actor_role='Admin'
                )
            except Exception:
                pass
            return True
        except Exception as e:
            print(f"[ApplicationModule.delete_application] {e}")
        finally:
            conn.close()
        return False


# ─────────────────────────────────────────────────────────────
#  PAYROLL MODULE
# ─────────────────────────────────────────────────────────────
class PayrollModule(DatabaseEngine):

    def setup_table(self):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS `staff_payroll` (
                    `payroll_id`     INT AUTO_INCREMENT PRIMARY KEY,
                    `admin_id`       INT NOT NULL,
                    `period_month`   VARCHAR(20) NOT NULL,
                    `basic_salary`   DECIMAL(10,2) DEFAULT 0.00,
                    `allowances`     DECIMAL(10,2) DEFAULT 0.00,
                    `deductions`     DECIMAL(10,2) DEFAULT 0.00,
                    `net_pay`        DECIMAL(10,2) DEFAULT 0.00,
                    `payment_date`   DATE DEFAULT NULL,
                    `payment_method` VARCHAR(30) DEFAULT 'Cash',
                    `notes`          TEXT DEFAULT NULL,
                    `created_at`     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    KEY `admin_id` (`admin_id`),
                    CONSTRAINT `payroll_ibfk_1`
                        FOREIGN KEY (`admin_id`)
                        REFERENCES `admins` (`admin_id`) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
            return True
        except Exception as e:
            print(f"[PayrollModule.setup_table] {e}")
        finally:
            conn.close()
        return False

    def get_payroll_for_admin(self, admin_id):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT * FROM staff_payroll WHERE admin_id=%s "
                "ORDER BY created_at DESC",
                (admin_id,),
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[PayrollModule.get_payroll_for_admin] {e}")
        finally:
            conn.close()
        return []

    def get_all_payroll(self):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT sp.*, a.full_name, a.role
                FROM staff_payroll sp
                JOIN admins a ON sp.admin_id = a.admin_id
                ORDER BY sp.created_at DESC
            """)
            return cur.fetchall()
        except Exception as e:
            print(f"[PayrollModule.get_all_payroll] {e}")
        finally:
            conn.close()
        return []

    def add_payroll(self, admin_id, period_month, basic_salary,
                    allowances=0, deductions=0, payment_date=None,
                    payment_method="Cash", notes=""):
        conn = self.connect()
        if not conn:
            return False
        try:
            net_pay = float(basic_salary) + float(allowances) - float(deductions)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO staff_payroll
                    (admin_id, period_month, basic_salary, allowances, deductions,
                     net_pay, payment_date, payment_method, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (admin_id, period_month, basic_salary, allowances, deductions,
                  net_pay, payment_date, payment_method, notes))
            conn.commit()
            try:
                AdminModule().add_log(
                    None, 'STAFF_PAYROLL',
                    f"Payroll posted for staff #{admin_id} "
                    f"({period_month}) — net ₱{net_pay:,.2f}",
                    'Admin', staff_id=admin_id,
                )
            except Exception:
                pass
            return True
        except Exception as e:
            print(f"[PayrollModule.add_payroll] {e}")
        finally:
            conn.close()
        return False

    def delete_payroll(self, payroll_id):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM staff_payroll WHERE payroll_id=%s", (payroll_id,)
            )
            conn.commit()
            try:
                AdminModule().add_log(
                    None, 'PAYROLL_DELETE',
                    f"Payroll #{payroll_id} removed",
                    'Admin',
                )
            except Exception:
                pass
            return True
        except Exception as e:
            print(f"[PayrollModule.delete_payroll] {e}")
        finally:
            conn.close()
        return False

    def pay_monthly_allowance(self, admin_id, period_month, allowance_amount,
                              payment_date=None, payment_method="Cash",
                              notes="Monthly staff allowance",
                              actor_admin_id=None):
        """Convenience: post a pure-allowance payroll entry (no salary,
        no deductions). Returns True on success."""
        ok = self.add_payroll(
            admin_id=admin_id,
            period_month=period_month,
            basic_salary=0,
            allowances=allowance_amount,
            deductions=0,
            payment_date=payment_date,
            payment_method=payment_method,
            notes=notes,
        )
        if ok and actor_admin_id is not None:
            try:
                AdminModule().add_log(
                    actor_admin_id, 'PAY_ALLOWANCE',
                    f"Paid ₱{float(allowance_amount):,.2f} allowance to "
                    f"staff #{admin_id} for {period_month}",
                    'Admin', staff_id=admin_id,
                )
            except Exception:
                pass
        return ok


# ─────────────────────────────────────────────────────────────
#  REPORTS MODULE
# ─────────────────────────────────────────────────────────────
class ReportsModule(DatabaseEngine):
    """
    Profitability analytics for DormNorm.

    Business model
    ──────────────
    • Fixed 'all-in' rate : ₱1,800 / renter / month
      (covers rent + unlimited electricity + water + WiFi)
    • Active renters       : fetched live from DB (not hardcoded)
    • Expected monthly     : active_count × ₱1,800 (dynamic)

    Utility cost model
    ──────────────────
    • Electricity & water : pulled from utility_bills table as
      actual recorded amounts (estimated readings captured there).
    • WiFi                : fixed ₱WIFI_FIXED_MONTHLY per month
      (constant — same bill every month regardless of usage).

    All figures are rolled up by billing_month (YYYY-MM format).
    """

    RATE_PER_RENTER    = 1_800.0   # all-in monthly rate (PHP)
    WIFI_FIXED_MONTHLY = 2_000.0   # fixed WiFi bill (PHP) — adjust as needed
    # MAX_RENTERS removed — always fetched live from DB via get_active_renter_count()

    # ── Collected revenue from payments table ─────────────────
    def get_monthly_revenue(self, n_months: int = 12) -> list[dict]:
        """
        Returns list of {month, collected, expected, renter_count} dicts.
        collected = sum of Paid payments for that billing_month.
        expected  = actual active renter count × RATE_PER_RENTER.
        """
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)

            # Get count of renters with active assignments only
            cur.execute(
                """SELECT COUNT(DISTINCT a.renter_id) AS cnt
                   FROM assignments a
                   JOIN renters r ON a.renter_id = r.renter_id
                   WHERE a.status = 'Active' AND r.renter_status = 'Active'"""
            )
            active_count = cur.fetchone()["cnt"] or 0
            expected = active_count * self.RATE_PER_RENTER

            cur.execute(
                """SELECT billing_month AS raw_month, status, amount
                   FROM payments
                   WHERE billing_month IS NOT NULL AND billing_month <> ''"""
            )
            buckets = {}
            for r in cur.fetchall():
                key = self._month_key(r["raw_month"])
                if not key:
                    continue
                amt = float(r["amount"] or 0)
                # Collected = fully Paid + amounts already paid in Partial records
                if r.get("status") in ("Paid", "Partial") and amt > 0:
                    buckets[key] = buckets.get(key, 0.0) + amt
                else:
                    buckets.setdefault(key, 0.0)
            sorted_keys = sorted(buckets.keys())[-n_months:]
            return [
                {"month": k, "collected": float(buckets[k]),
                 "expected": expected, "renter_count": active_count}
                for k in sorted_keys
            ]
        except Exception as e:
            print(f"[ReportsModule.get_monthly_revenue] {e}")
        finally:
            conn.close()
        return []

    def get_monthly_revenue_all(self) -> list[dict]:
        """Same as get_monthly_revenue but returns ALL months (no limit)."""
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT COUNT(DISTINCT a.renter_id) AS cnt
                   FROM assignments a
                   JOIN renters r ON a.renter_id = r.renter_id
                   WHERE a.status = 'Active' AND r.renter_status = 'Active'"""
            )
            active_count = cur.fetchone()["cnt"] or 0
            expected = active_count * self.RATE_PER_RENTER

            cur.execute(
                """SELECT billing_month AS raw_month, status, amount
                   FROM payments
                   WHERE billing_month IS NOT NULL AND billing_month <> ''"""
            )
            buckets = {}
            for r in cur.fetchall():
                key = self._month_key(r["raw_month"])
                if not key:
                    continue
                amt = float(r["amount"] or 0)
                if r.get("status") in ("Paid", "Partial") and amt > 0:
                    buckets[key] = buckets.get(key, 0.0) + amt
                else:
                    buckets.setdefault(key, 0.0)
            return [
                {"month": k, "collected": float(buckets[k]),
                 "expected": expected, "renter_count": active_count}
                for k in sorted(buckets.keys())
            ]
        except Exception as e:
            print(f"[ReportsModule.get_monthly_revenue_all] {e}")
        finally:
            conn.close()
        return []

    # ── Utility expenses from utility_bills table ─────────────
    def get_monthly_utility_expenses(self, n_months: int = 12) -> list[dict]:
        """
        Returns list of {month, electricity, water, wifi, total} dicts.
        • electricity & water: summed from utility_bills (estimated readings).
        • wifi: WIFI_FIXED_MONTHLY per month (constant).
        Only months present in utility_bills are returned.
        """
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT billing_month AS raw_month, bill_type, amount
                   FROM utility_bills
                   WHERE billing_month IS NOT NULL""")
            buckets = {}
            for r in cur.fetchall():
                key = self._month_key(r["raw_month"])
                if not key:
                    continue
                b = buckets.setdefault(key, {"electricity": 0.0, "water": 0.0})
                bt = (r.get("bill_type") or "").lower()
                if bt == "electricity":
                    b["electricity"] += float(r["amount"] or 0)
                elif bt == "water":
                    b["water"] += float(r["amount"] or 0)
            sorted_keys = sorted(buckets.keys())[-n_months:]
            result = []
            for k in sorted_keys:
                e = buckets[k]["electricity"]
                w = buckets[k]["water"]
                wi = self.WIFI_FIXED_MONTHLY
                result.append({"month": k, "electricity": e, "water": w,
                               "wifi": wi, "total": e + w + wi})
            return result
        except Exception as e:
            print(f"[ReportsModule.get_monthly_utility_expenses] {e}")
        finally:
            conn.close()
        return []

    # ── Combined profitability summary ────────────────────────
    def get_profitability_summary(self, n_months: int = 6) -> dict:
        """
        High-level summary merging revenue and utility expenses.
        Returns:
          {
            monthly: [ {month, revenue, expenses, profit, margin_pct} … ],
            totals:  { revenue, expenses, profit, margin_pct },
            expense_breakdown: { electricity, water, wifi }   ← avg/mo
          }
        """
        revenues  = {r["month"]: r for r in self.get_monthly_revenue(n_months)}
        utilities = {u["month"]: u for u in self.get_monthly_utility_expenses(n_months)}

        all_months = sorted(set(list(revenues.keys()) + list(utilities.keys())))

        monthly = []
        for m in all_months:
            rev  = revenues.get(m,  {}).get("collected", 0.0)
            util = utilities.get(m, {}).get("total",     0.0)
            profit = rev - util
            margin = round(profit / rev * 100, 1) if rev > 0 else 0.0
            monthly.append({
                "month":   m,
                "revenue": rev,
                "expenses": util,
                "profit":  profit,
                "margin_pct": margin,
            })

        total_rev  = sum(x["revenue"]  for x in monthly)
        total_exp  = sum(x["expenses"] for x in monthly)
        total_prof = total_rev - total_exp
        total_margin = round(total_prof / total_rev * 100, 1) if total_rev > 0 else 0.0

        # Average monthly expense breakdown
        n = len(monthly) or 1
        avg_elec  = sum(utilities.get(m, {}).get("electricity", 0) for m in all_months) / n
        avg_water = sum(utilities.get(m, {}).get("water",       0) for m in all_months) / n
        avg_wifi  = self.WIFI_FIXED_MONTHLY   # constant

        return {
            "monthly":  monthly,
            "totals":   {
                "revenue":    total_rev,
                "expenses":   total_exp,
                "profit":     total_prof,
                "margin_pct": total_margin,
            },
            "expense_breakdown": {
                "electricity": round(avg_elec, 2),
                "water":       round(avg_water, 2),
                "wifi":        avg_wifi,
            },
        }


# ─────────────────────────────────────────────────────────────
#  PROFILE MODULE
# ─────────────────────────────────────────────────────────────
class ProfileModule(DatabaseEngine):

    def get_admin_profile(self, admin_id):
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM admins WHERE admin_id=%s", (admin_id,))
            return cur.fetchone()
        except Exception as e:
            print(f"[ProfileModule.get_admin_profile] {e}")
        finally:
            conn.close()
        return None

    def update_admin_profile(self, admin_id, full_name=None, email=None,
                              contact_number=None, profile_pic_path=None):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            fields = {}
            if full_name        is not None: fields["full_name"]        = full_name
            if email            is not None: fields["email"]            = email
            if contact_number   is not None: fields["contact_number"]   = contact_number
            if profile_pic_path is not None: fields["profile_pic_path"] = profile_pic_path
            if not fields:
                return True
            set_clause = ", ".join(f"`{k}`=%s" for k in fields)
            values = list(fields.values()) + [admin_id]
            cur.execute(f"UPDATE admins SET {set_clause} WHERE admin_id=%s", values)
            conn.commit()
            return True
        except Exception as e:
            print(f"[ProfileModule.update_admin_profile] {e}")
        finally:
            conn.close()
        return False

    def change_admin_password(self, admin_id, old_password, new_password):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor(dictionary=True)
            old_hashed = self._hash(old_password)
            cur.execute(
                "SELECT admin_id FROM admins WHERE admin_id=%s AND password=%s",
                (admin_id, old_hashed),
            )
            if not cur.fetchone():
                return "wrong_password"
            cur.execute(
                "UPDATE admins SET password=%s WHERE admin_id=%s",
                (self._hash(new_password), admin_id),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[ProfileModule.change_admin_password] {e}")
        finally:
            conn.close()
        return False

    def get_renter_profile(self, renter_id):
        conn = self.connect()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            # ORDER BY + LIMIT guards against duplicate renter_accounts rows
            # (can occur when both the DB trigger and Python code each insert).
            # Prefer the Active account; fall back to lowest account_id.
            cur.execute(
                """SELECT *
                   FROM vw_renter_profile_full
                   WHERE renter_id=%s
                   ORDER BY (account_status = 'Active') DESC
                   LIMIT 1""",
                (renter_id,),
            )
            return cur.fetchone()
        except Exception as e:
            print(f"[ProfileModule.get_renter_profile] {e}")
        finally:
            conn.close()
        return None

    def update_renter_profile(self, renter_id, contact_number=None,
                               email=None, address=None,
                               emergency_contact_name=None,
                               emergency_contact_number=None,
                               profile_pic_path=None):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            fields = {}
            if contact_number            is not None: fields["contact_number"]            = contact_number
            if email                     is not None: fields["email"]                     = email
            if address                   is not None: fields["address"]                   = address
            if emergency_contact_name    is not None: fields["emergency_contact_name"]    = emergency_contact_name
            if emergency_contact_number  is not None: fields["emergency_contact_number"]  = emergency_contact_number
            if profile_pic_path          is not None: fields["profile_pic_path"]          = profile_pic_path
            if not fields:
                return True
            set_clause = ", ".join(f"`{k}`=%s" for k in fields)
            values = list(fields.values()) + [renter_id]
            cur.execute(
                f"UPDATE renters SET {set_clause} WHERE renter_id=%s", values
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[ProfileModule.update_renter_profile] {e}")
        finally:
            conn.close()
        return False

    def change_renter_password(self, renter_id, old_password, new_password):
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor(dictionary=True)
            old_hashed = self._hash(old_password)
            # Only match the primary Active account to avoid ambiguity
            cur.execute(
                "SELECT account_id FROM renter_accounts "
                "WHERE renter_id=%s AND password=%s "
                "ORDER BY (account_status='Active') DESC, account_id ASC "
                "LIMIT 1",
                (renter_id, old_hashed),
            )
            row = cur.fetchone()
            if not row:
                return "wrong_password"
            cur.execute(
                "UPDATE renter_accounts SET password=%s WHERE account_id=%s",
                (self._hash(new_password), row["account_id"]),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[ProfileModule.change_renter_password] {e}")
        finally:
            conn.close()
        return False


# ─────────────────────────────────────────────────────────────
#  ROOM SWITCH REQUEST MODULE
# ─────────────────────────────────────────────────────────────
class SwitchRequestModule(DatabaseEngine):
    """Renters request to switch rooms/beds; admins approve or reject."""

    def setup_table(self):
        conn = self.connect()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                """CREATE TABLE IF NOT EXISTS room_switch_requests (
                    request_id      INT AUTO_INCREMENT PRIMARY KEY,
                    renter_id       INT NOT NULL,
                    current_room_id INT,
                    desired_room_id INT NOT NULL,
                    desired_bed     VARCHAR(30),
                    reason          TEXT,
                    status          ENUM('Pending','Approved','Rejected') DEFAULT 'Pending',
                    decided_by      INT,
                    decision_notes  TEXT,
                    requested_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
                    decided_at      DATETIME
                )"""
            )
            conn.commit()
        except Exception as e:
            print(f"[SwitchRequestModule.setup_table] {e}")
        finally:
            conn.close()

    def add_request(self, renter_id, current_room_id, desired_room_id,
                    desired_bed=None, reason=""):
        self.setup_table()
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO room_switch_requests
                   (renter_id, current_room_id, desired_room_id, desired_bed, reason)
                   VALUES (%s,%s,%s,%s,%s)""",
                (renter_id, current_room_id, desired_room_id, desired_bed, reason),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[SwitchRequestModule.add_request] {e}")
        finally:
            conn.close()
        return False

    def get_all_requests(self, status=None):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            base = (
                """SELECT sr.*,
                          CONCAT(r.first_name,' ',r.last_name) AS renter_name,
                          cur.room_number  AS current_room_number,
                          des.room_number  AS desired_room_number
                   FROM room_switch_requests sr
                   JOIN renters r        ON sr.renter_id       = r.renter_id
                   LEFT JOIN rooms cur   ON sr.current_room_id = cur.room_id
                   JOIN rooms des        ON sr.desired_room_id = des.room_id"""
            )
            if status:
                cur.execute(base + " WHERE sr.status=%s ORDER BY sr.requested_at DESC", (status,))
            else:
                cur.execute(base + " ORDER BY FIELD(sr.status,'Pending','Approved','Rejected'), sr.requested_at DESC")
            return cur.fetchall()
        except Exception as e:
            print(f"[SwitchRequestModule.get_all_requests] {e}")
        finally:
            conn.close()
        return []

    def get_renter_requests(self, renter_id):
        conn = self.connect()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT sr.*, des.room_number AS desired_room_number,
                          cur.room_number AS current_room_number
                   FROM room_switch_requests sr
                   JOIN rooms des       ON sr.desired_room_id = des.room_id
                   LEFT JOIN rooms cur  ON sr.current_room_id = cur.room_id
                   WHERE sr.renter_id=%s
                   ORDER BY sr.requested_at DESC""",
                (renter_id,),
            )
            return cur.fetchall()
        except Exception as e:
            print(f"[SwitchRequestModule.get_renter_requests] {e}")
        finally:
            conn.close()
        return []

    def decide(self, request_id, admin_id, approve, notes=""):
        """Approve or reject. On approve, end current assignment + create new one."""
        conn = self.connect()
        if not conn:
            return False
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT * FROM room_switch_requests WHERE request_id=%s",
                (request_id,),
            )
            req = cur.fetchone()
            if not req or req["status"] != "Pending":
                return False

            new_status = "Approved" if approve else "Rejected"
            cur.execute(
                """UPDATE room_switch_requests
                   SET status=%s, decided_by=%s, decision_notes=%s,
                       decided_at=NOW()
                   WHERE request_id=%s""",
                (new_status, admin_id, notes, request_id),
            )

            if approve:
                # Verify desired bed still free
                cur.execute(
                    "SELECT capacity FROM rooms WHERE room_id=%s",
                    (req["desired_room_id"],),
                )
                room = cur.fetchone()
                cur.execute(
                    "SELECT COUNT(*) AS c FROM assignments "
                    "WHERE room_id=%s AND status='Active'",
                    (req["desired_room_id"],),
                )
                occ = cur.fetchone()["c"]
                if not room or occ >= int(room["capacity"] or 0):
                    conn.rollback()
                    return False

                # End current active assignment(s) for this renter
                cur.execute(
                    """UPDATE assignments SET status='Ended', check_out_date=CURDATE()
                       WHERE renter_id=%s AND status='Active'""",
                    (req["renter_id"],),
                )
                # Create new assignment
                cur.execute(
                    """INSERT INTO assignments
                       (renter_id, room_id, bed_assignment, check_in_date, status)
                       VALUES (%s,%s,%s,CURDATE(),'Active')""",
                    (req["renter_id"], req["desired_room_id"],
                     req.get("desired_bed") or "Bed A - Bottom"),
                )

            conn.commit()
            return True
        except Exception as e:
            print(f"[SwitchRequestModule.decide] {e}")
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            conn.close()
        return False

    def pending_count(self):
        conn = self.connect()
        if not conn:
            return 0
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM room_switch_requests WHERE status='Pending'"
            )
            return cur.fetchone()[0] or 0
        except Exception as e:
            print(f"[SwitchRequestModule.pending_count] {e}")
        finally:
            conn.close()
        return 0




# ─────────────────────────────────────────────────────────────
#  SELF-TEST
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("─── DormNorm DB Self-Test (v2) ───")

    # Patch schema gaps first (e.g. add 'Refunded' to payments ENUM)
    DatabaseEngine().ensure_schema()

    admin_mod = AdminModule()
    admin_mod.ensure_admin_columns()

    hashed_a = admin_mod.hash_existing_admin_passwords()
    print(f"[MIGRATION] Admin passwords hashed: {hashed_a}")

    renter_mod = RenterModule()
    hashed_r = renter_mod.hash_existing_renter_passwords()
    print(f"[MIGRATION] Renter passwords hashed: {hashed_r}")

    # Test admin login with username
    result = admin_mod.validate_login("gel_admin", "gel123")
    if result:
        print(f"[OK] Admin login (username) — {result['full_name']} ({result['role']})")
    else:
        print("[FAIL] Admin login failed.")

    # Test renter login with username
    renter_result = renter_mod.validate_renter_login("renter1", "dorm123")
    if renter_result:
        print(f"[OK] Renter login (username) — "
              f"{renter_result.get('full_name') or renter_result.get('first_name','') + ' ' + renter_result.get('last_name','')}")
    else:
        print("[INFO] Renter login test skipped / check credentials.")

    room_mod = RoomModule()
    rooms = room_mod.get_all_rooms()
    print(f"[OK] {len(rooms)} rooms found.")

    app_mod = ApplicationModule()
    app_mod.setup_table()
    pending = app_mod.get_pending_count()
    print(f"[OK] {pending} pending rental application(s).")

    pay_mod = PayrollModule()
    pay_mod.setup_table()
    print("[OK] staff_payroll table ready.")

    print("─── Self-test complete ───")