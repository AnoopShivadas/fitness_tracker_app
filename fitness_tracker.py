import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import hashlib
import os
from datetime import date

class FitnessTrackerApp:
    """
    A simple fitness tracker application with user login, registration,
    workout logging, history, and summary. Data is stored in a local SQLite database.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Fitness Tracker")
        # Initialize DB connection
        self.conn = sqlite3.connect("fitness_tracker.db")
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.current_user_id = None

        # Setup frames for login and main application
        self.login_frame = tk.Frame(self.root, padx=20, pady=20)
        self.main_frame = tk.Frame(self.root, padx=10, pady=10)
        self.login_frame.pack()

        self.setup_login_frame()
        # Main frame is created but not packed until after login
        self.setup_main_frame()

    def create_tables(self):
        """Create the users and workouts tables if they do not exist."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                duration INTEGER,
                calories INTEGER,
                weight REAL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        self.conn.commit()

    def setup_login_frame(self):
        """Create widgets for the login interface."""
        tk.Label(self.login_frame, text="Login to Fitness Tracker", font=("Helvetica", 25)
                ).grid(row=0, column=0, columnspan=2, pady=(0, 10))
        tk.Label(self.login_frame, text="Username:").grid(row=1, column=0, sticky='e')
        self.username_entry = tk.Entry(self.login_frame)
        self.username_entry.grid(row=1, column=1, pady=5)
        tk.Label(self.login_frame, text="Password:").grid(row=2, column=0, sticky='e')
        self.password_entry = tk.Entry(self.login_frame, show="*")
        self.password_entry.grid(row=2, column=1, pady=5)
        tk.Button(self.login_frame, text="Login", width=10, command=self.login
                  ).grid(row=3, column=0, pady=10)
        tk.Button(self.login_frame, text="Register", width=10, command=self.open_register_window
                  ).grid(row=3, column=1)

    def open_register_window(self):
        """Open a window for new user registration."""
        reg_window = tk.Toplevel(self.root)
        reg_window.title("Register")
        tk.Label(reg_window, text="Create a New Account", font=("Helvetica", 14)
                ).grid(row=0, column=0, columnspan=2, pady=(0, 10))
        tk.Label(reg_window, text="Username:").grid(row=1, column=0, sticky='e')
        new_user_entry = tk.Entry(reg_window)
        new_user_entry.grid(row=1, column=1, pady=5)
        tk.Label(reg_window, text="Password:").grid(row=2, column=0, sticky='e')
        new_pass_entry = tk.Entry(reg_window, show="*")
        new_pass_entry.grid(row=2, column=1, pady=5)
        tk.Label(reg_window, text="Confirm Password:").grid(row=3, column=0, sticky='e')
        confirm_pass_entry = tk.Entry(reg_window, show="*")
        confirm_pass_entry.grid(row=3, column=1, pady=5)
        def attempt_register():
            username = new_user_entry.get().strip()
            pw = new_pass_entry.get()
            cpw = confirm_pass_entry.get()
            if not username or not pw:
                messagebox.showerror("Error", "Username and password cannot be empty.")
                return
            if pw != cpw:
                messagebox.showerror("Error", "Passwords do not match.")
                return
            # Check if user exists
            self.cursor.execute("SELECT id FROM users WHERE username=?", (username,))
            if self.cursor.fetchone():
                messagebox.showerror("Error", "Username already exists.")
                return
            # Hash password with salt using PBKDF2 (sha256)
            salt = os.urandom(16)
            hash_pw = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt, 100000)
            # Store hex values in DB
            self.cursor.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                (username, hash_pw.hex(), salt.hex()))
            self.conn.commit()
            messagebox.showinfo("Success", "Account created! You can now log in.")
            reg_window.destroy()
        tk.Button(reg_window, text="Register", width=10, command=attempt_register
                  ).grid(row=4, column=0, pady=10)
        tk.Button(reg_window, text="Cancel", width=10, command=reg_window.destroy
                  ).grid(row=4, column=1)

    def login(self):
        """Verify login credentials and show main app if successful."""
        username = self.username_entry.get().strip()
        pw = self.password_entry.get()
        if not username or not pw:
            messagebox.showerror("Error", "Please enter username and password.")
            return
        self.cursor.execute("SELECT id, password_hash, salt FROM users WHERE username=?", (username,))
        result = self.cursor.fetchone()
        if not result:
            messagebox.showerror("Error", "Invalid username or password.")
            return
        user_id, stored_hash, stored_salt = result
        test_hash = hashlib.pbkdf2_hmac('sha256', pw.encode(), bytes.fromhex(stored_salt), 100000)
        if test_hash.hex() != stored_hash:
            messagebox.showerror("Error", "Invalid username or password.")
            return
        # Login successful
        self.current_user_id = user_id
        self.username_entry.delete(0, 'end')
        self.password_entry.delete(0, 'end')
        self.login_frame.pack_forget()  # hide login frame
        self.welcome_label.config(text=f"Welcome, {username}!")
        self.main_frame.pack(fill='both', expand=True)  # show main app
        self.refresh_history()
        self.update_summary()

    def logout(self):
        """Log out the current user and return to the login screen."""
        self.main_frame.pack_forget()
        self.current_user_id = None
        self.login_frame.pack()

    def setup_main_frame(self):
        """Create the main interface (tabs for Log, History, Summary)."""
        # Top bar with welcome and logout
        top_frame = tk.Frame(self.main_frame)
        top_frame.pack(fill='x', pady=(0, 10))
        self.welcome_label = tk.Label(top_frame, text="Welcome!", font=("Helvetica", 14))
        self.welcome_label.pack(side='left')
        logout_button = tk.Button(top_frame, text="Logout", command=self.logout)
        logout_button.pack(side='right')

        # Notebook (tabbed interface)
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill='both', expand=True)

        # --- Tab: Log Workout ---
        self.log_frame = tk.Frame(notebook, padx=10, pady=10)
        notebook.add(self.log_frame, text="Log Workout")
        tk.Label(self.log_frame, text="Date (YYYY-MM-DD):"
                ).grid(row=0, column=0, sticky='e')
        self.date_entry = tk.Entry(self.log_frame)
        self.date_entry.insert(0, date.today().isoformat())  # default to today
        self.date_entry.grid(row=0, column=1, pady=5)
        tk.Label(self.log_frame, text="Workout Type:"
                ).grid(row=1, column=0, sticky='e')
        self.type_var = tk.StringVar()
        types = ["Running", "Cycling", "Weightlifting", "Swimming", "Yoga", "Other"]
        self.type_combo = ttk.Combobox(self.log_frame, textvariable=self.type_var,
                                       values=types, state='readonly')
        self.type_combo.current(0)
        self.type_combo.grid(row=1, column=1, pady=5)
        tk.Label(self.log_frame, text="Duration (minutes):"
                ).grid(row=2, column=0, sticky='e')
        self.duration_entry = tk.Entry(self.log_frame)
        self.duration_entry.grid(row=2, column=1, pady=5)
        tk.Label(self.log_frame, text="Calories Burned:"
                ).grid(row=3, column=0, sticky='e')
        self.calories_entry = tk.Entry(self.log_frame)
        self.calories_entry.grid(row=3, column=1, pady=5)
        tk.Label(self.log_frame, text="Current Weight (kg):"
                ).grid(row=4, column=0, sticky='e')
        self.weight_entry = tk.Entry(self.log_frame)
        self.weight_entry.grid(row=4, column=1, pady=5)
        tk.Button(self.log_frame, text="Add Workout", command=self.add_workout
                  ).grid(row=5, column=0, columnspan=2, pady=10)

        # --- Tab: Workout History ---
        self.history_frame = tk.Frame(notebook, padx=10, pady=10)
        notebook.add(self.history_frame, text="Workout History")
        cols = ("Date", "Type", "Duration", "Calories", "Weight")
        self.tree = ttk.Treeview(self.history_frame, columns=cols, show='headings')
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100)
        self.tree.pack(fill='both', expand=True)

        # --- Tab: Summary ---
        self.summary_frame = tk.Frame(notebook, padx=10, pady=10)
        notebook.add(self.summary_frame, text="Summary")
        self.total_workouts_label = tk.Label(self.summary_frame, text="")
        self.total_workouts_label.pack(pady=5)
        self.total_calories_label = tk.Label(self.summary_frame, text="")
        self.total_calories_label.pack(pady=5)
        self.weight_change_label = tk.Label(self.summary_frame, text="")
        self.weight_change_label.pack(pady=5)

    def add_workout(self):
        """Add a new workout entry for the current user."""
        if not self.current_user_id:
            messagebox.showerror("Error", "No user is currently logged in.")
            return
        d = self.date_entry.get().strip()
        wtype = self.type_var.get()
        # Validate numeric fields
        try:
            duration = int(self.duration_entry.get().strip())
            calories = int(self.calories_entry.get().strip())
            weight = float(self.weight_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Enter valid numbers for duration, calories, and weight.")
            return
        if not d:
            messagebox.showerror("Error", "Please enter the date.")
            return
        # Insert into database
        self.cursor.execute(
            "INSERT INTO workouts (user_id, date, type, duration, calories, weight) VALUES (?, ?, ?, ?, ?, ?)",
            (self.current_user_id, d, wtype, duration, calories, weight)
        )
        self.conn.commit()
        messagebox.showinfo("Success", "Workout logged successfully.")
        # Clear input fields (except date)
        self.duration_entry.delete(0, 'end')
        self.calories_entry.delete(0, 'end')
        self.weight_entry.delete(0, 'end')
        # Refresh history and summary
        self.refresh_history()
        self.update_summary()

    def refresh_history(self):
        """Load workouts from the database and display in the table."""
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.cursor.execute(
            "SELECT date, type, duration, calories, weight FROM workouts WHERE user_id=? ORDER BY date",
            (self.current_user_id,)
        )
        for row in self.cursor.fetchall():
            self.tree.insert("", "end", values=row)

    def update_summary(self):
        """Calculate and display summary statistics for the user."""
        self.cursor.execute("SELECT COUNT(*), SUM(calories) FROM workouts WHERE user_id=?", (self.current_user_id,))
        count, total_cal = self.cursor.fetchone()
        total_cal = total_cal or 0
        self.cursor.execute("SELECT weight FROM workouts WHERE user_id=? ORDER BY date", (self.current_user_id,))
        weights = [w[0] for w in self.cursor.fetchall()]
        if weights:
            start_weight = weights[0]
            end_weight = weights[-1]
            change = end_weight - start_weight
            self.total_workouts_label.config(text=f"Total workouts: {count}")
            self.total_calories_label.config(text=f"Total calories burned: {total_cal}")
            self.weight_change_label.config(
                text=f"Weight: {start_weight} kg \u2192 {end_weight} kg (change: {change:+.2f} kg)"
            )
        else:
            self.total_workouts_label.config(text="No workouts logged yet.")
            self.total_calories_label.config(text="")
            self.weight_change_label.config(text="")

def main():
    root = tk.Tk()
    app = FitnessTrackerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
