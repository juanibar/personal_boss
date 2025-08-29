
import sqlite3
import os
import sys
import shutil
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

APP_TITLE = "Personal Boss"

def _get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _get_base_dir()
DB_PATH = os.path.join(BASE_DIR, "personal_boss.db")
LEGACY_DB_PATH = os.path.join(os.path.expanduser("~"), ".personal_boss.db")

DEFAULT_TAGS = [
    "prioridad A",
    "prioridad B",
    "prioridad C",
    "prioridad D",
    "casa",
    "trabajo",
    "mañana",
    "tarde",
    "noche",
]

# ---------------------------- DB Helpers ---------------------------- #

def ensure_db_location():
    if not os.path.exists(DB_PATH) and os.path.exists(LEGACY_DB_PATH):
        try:
            shutil.copy2(LEGACY_DB_PATH, DB_PATH)
        except Exception as e:
            print(f"Advertencia: no se pudo migrar la DB legacy: {e}")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            is_complete INTEGER NOT NULL DEFAULT 0,
            position INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS action_tags (
            action_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (action_id, tag_id),
            FOREIGN KEY(action_id) REFERENCES actions(id) ON DELETE CASCADE,
            FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    """)
    conn.commit()

    for t in DEFAULT_TAGS:
        try:
            cur.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (t,))
        except sqlite3.Error:
            pass
    conn.commit()
    conn.close()

def list_projects():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM projects ORDER BY created_at ASC")
    rows = cur.fetchall()
    conn.close()
    return rows

def create_project(name):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cur.execute("INSERT INTO projects(name, created_at) VALUES (?, ?)", (name, now))
    conn.commit()
    conn.close()

def update_project(project_id, new_name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE projects SET name=? WHERE id=?", (new_name, project_id))
    conn.commit()
    conn.close()

def delete_project(project_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM projects WHERE id=?", (project_id,))
    conn.commit()
    conn.close()

def list_actions(project_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.*, p.name as project_name
        FROM actions a
        JOIN projects p ON p.id = a.project_id
        WHERE a.project_id=?
        ORDER BY a.is_complete ASC, a.created_at ASC
    """, (project_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_action_tags(action_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.* FROM tags t
        JOIN action_tags at ON at.tag_id = t.id
        WHERE at.action_id = ?
        ORDER BY t.name COLLATE NOCASE
    """, (action_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def create_action(project_id, description, tag_ids):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cur.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM actions WHERE project_id=?", (project_id,))
    position = cur.fetchone()[0]
    cur.execute("""
        INSERT INTO actions(project_id, description, is_complete, position, created_at)
        VALUES (?, ?, 0, ?, ?)
    """, (project_id, description, position, now))
    action_id = cur.lastrowid
    for tid in tag_ids:
        cur.execute("INSERT OR IGNORE INTO action_tags(action_id, tag_id) VALUES (?, ?)", (action_id, tid))
    conn.commit()
    conn.close()
    return action_id

def update_action(action_id, description, tag_ids, is_complete=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE actions SET description=? WHERE id=?", (description, action_id))
    if is_complete is not None:
        cur.execute("UPDATE actions SET is_complete=? WHERE id=?", (1 if is_complete else 0, action_id))
    cur.execute("DELETE FROM action_tags WHERE action_id=?", (action_id,))
    for tid in tag_ids:
        cur.execute("INSERT OR IGNORE INTO action_tags(action_id, tag_id) VALUES (?, ?)", (action_id, tid))
    conn.commit()
    conn.close()

def toggle_action_status(action_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT is_complete FROM actions WHERE id=?", (action_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return
    new_val = 0 if row[0] else 1
    cur.execute("UPDATE actions SET is_complete=? WHERE id=?", (new_val, action_id))
    conn.commit()
    conn.close()

def delete_action(action_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM actions WHERE id=?", (action_id,))
    conn.commit()
    conn.close()

def list_all_tags():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tags ORDER BY name COLLATE NOCASE ASC")
    rows = cur.fetchall()
    conn.close()
    return rows

def create_tag(name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO tags(name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def rename_tag(tag_id, new_name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE tags SET name=? WHERE id=?", (new_name, tag_id))
    conn.commit()
    conn.close()

def delete_tag(tag_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM tags WHERE id=?", (tag_id,))
    conn.commit()
    conn.close()

def find_next_action_by_tags(selected_tag_ids):
    conn = get_conn()
    cur = conn.cursor()
    if not selected_tag_ids:
        cur.execute("""
            SELECT a.*, p.name AS project_name
            FROM actions a
            JOIN projects p ON p.id = a.project_id
            WHERE a.is_complete = 0
            ORDER BY a.created_at ASC
            LIMIT 1
        """)
    else:
        placeholders = ",".join("?" * len(selected_tag_ids))
        query = f"""
            SELECT a.*, p.name AS project_name
            FROM actions a
            JOIN projects p ON p.id = a.project_id
            WHERE a.is_complete = 0
            AND a.id IN (
                SELECT action_id
                FROM action_tags
                WHERE tag_id IN ({placeholders})
                GROUP BY action_id
                HAVING COUNT(DISTINCT tag_id) = {len(selected_tag_ids)}
            )
            ORDER BY a.created_at ASC
            LIMIT 1
        """
        cur.execute(query, selected_tag_ids)
    row = cur.fetchone()
    conn.close()
    return row

# ---------------------------- UI Components ---------------------------- #

class TagManager(tk.Toplevel):
    def __init__(self, master, on_close=None):
        super().__init__(master)
        self.title("Gestionar etiquetas")
        self.geometry("460x420")
        self.on_close = on_close
        self.configure(padx=10, pady=10)

        # Search box
        ttk.Label(self, text="Buscar etiqueta:").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, columnspan=2, sticky="ew")
        self.grid_columnconfigure(1, weight=1)
        self.search_var.trace_add("write", lambda *args: self._apply_filter())

        # Tag list
        self.tag_list = tk.Listbox(self, height=12)
        self.tag_list.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(6,10))
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0)

        self.refresh_tags()

        ttk.Label(self, text="Nueva etiqueta:").grid(row=2, column=0, sticky="w")
        self.new_tag_entry = ttk.Entry(self)
        self.new_tag_entry.grid(row=2, column=1, sticky="ew")
        ttk.Button(self, text="Agregar", command=self.add_tag).grid(row=2, column=2, sticky="e")

        ttk.Label(self, text="Renombrar seleccionada a:").grid(row=3, column=0, sticky="w", pady=(10,0))
        self.rename_entry = ttk.Entry(self)
        self.rename_entry.grid(row=3, column=1, sticky="ew", pady=(10,0))
        ttk.Button(self, text="Renombrar", command=self.rename_selected).grid(row=3, column=2, pady=(10,0))

        ttk.Button(self, text="Eliminar seleccionada", command=self.delete_selected).grid(row=4, column=0, columnspan=3, pady=(12,0))

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        if self.on_close:
            self.on_close()
        self.destroy()

    def refresh_tags(self):
        self.all_tags = list_all_tags()
        self._apply_filter()

    def _apply_filter(self):
        term = (self.search_var.get() or "").strip().lower()
        if term:
            self.filtered_tags = [t for t in self.all_tags if term in t["name"].lower()]
        else:
            self.filtered_tags = list(self.all_tags)
        self.tag_list.delete(0, tk.END)
        for t in self.filtered_tags:
            self.tag_list.insert(tk.END, t["name"])

    def add_tag(self):
        name = self.new_tag_entry.get().strip()
        if not name:
            return
        try:
            create_tag(name)
            self.new_tag_entry.delete(0, tk.END)
            self.refresh_tags()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", f"La etiqueta '{name}' ya existe.")

    def _get_selected_tag_row(self):
        idx = self.tag_list.curselection()
        if not idx:
            return None
        return self.filtered_tags[idx[0]]

    def rename_selected(self):
        t = self._get_selected_tag_row()
        if not t:
            messagebox.showinfo("Info", "Selecciona una etiqueta para renombrar.")
            return
        new_name = self.rename_entry.get().strip()
        if not new_name:
            messagebox.showinfo("Info", "Ingresá el nuevo nombre.")
            return
        try:
            rename_tag(t["id"], new_name)
            self.rename_entry.delete(0, tk.END)
            self.refresh_tags()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", f"Ya existe una etiqueta con el nombre '{new_name}'.")

    def delete_selected(self):
        t = self._get_selected_tag_row()
        if not t:
            messagebox.showinfo("Info", "Selecciona una etiqueta para eliminar.")
            return
        if messagebox.askyesno("Confirmar", f"¿Eliminar etiqueta '{t['name']}'?\nEsto la quitará de las acciones que la tengan."):
            delete_tag(t["id"])
            self.refresh_tags()


class ActionEditor(tk.Toplevel):
    def __init__(self, master, project_id, action=None, on_save=None, refresh_tags_cb=None):
        super().__init__(master)
        self.title("Acción")
        self.geometry("620x520")
        self.project_id = project_id
        self.action = action
        self.on_save = on_save
        self.refresh_tags_cb = refresh_tags_cb

        self.configure(padx=10, pady=10)
        ttk.Label(self, text="Descripción:").grid(row=0, column=0, sticky="w")
        self.desc_entry = ttk.Entry(self, width=60)
        self.desc_entry.grid(row=0, column=1, columnspan=3, sticky="ew")
        self.grid_columnconfigure(1, weight=1)

        # Search + results for available tags
        ttk.Label(self, text="Buscar etiqueta:").grid(row=1, column=0, sticky="w", pady=(10,0))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self, textvariable=self.search_var)
        self.search_entry.grid(row=1, column=1, sticky="ew", pady=(10,0))
        self.search_var.trace_add("write", lambda *args: self._refresh_results())

        ttk.Button(self, text="Nueva etiqueta…", command=self.create_new_tag).grid(row=1, column=2, sticky="w", padx=(8,0), pady=(10,0))

        ttk.Label(self, text="Etiquetas disponibles (doble clic para añadir):").grid(row=2, column=0, columnspan=2, sticky="w", pady=(8,0))
        results_frame = ttk.Frame(self)
        results_frame.grid(row=3, column=0, columnspan=3, sticky="nsew")
        self.grid_rowconfigure(3, weight=1)
        self.available_list = tk.Listbox(results_frame, height=10, selectmode=tk.BROWSE)
        vscroll_av = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.available_list.yview)
        self.available_list.configure(yscrollcommand=vscroll_av.set)
        self.available_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vscroll_av.pack(side=tk.RIGHT, fill=tk.Y)
        self.available_list.bind("<Double-1>", lambda e: self.add_selected_from_results())
        # Enter in search adds first result
        self.search_entry.bind("<Return>", lambda e: self.add_selected_from_results(first_only=True))

        ttk.Button(self, text="Añadir seleccionada", command=self.add_selected_from_results).grid(row=4, column=0, sticky="w", pady=(6,0))

        # Selected tags list
        ttk.Label(self, text="Etiquetas de la acción:").grid(row=5, column=0, sticky="w", pady=(10,0))
        self.selected_tags_list = tk.Listbox(self, height=8, selectmode=tk.SINGLE)
        self.selected_tags_list.grid(row=6, column=0, columnspan=2, sticky="nsew")
        self.grid_rowconfigure(6, weight=1)
        ttk.Button(self, text="Quitar etiqueta", command=self.remove_selected_tag).grid(row=6, column=2, sticky="n", padx=(8,0))

        self.status_var = tk.BooleanVar(value=False)
        self.status_check = ttk.Checkbutton(self, text="Marcar como completada", variable=self.status_var)
        self.status_check.grid(row=7, column=0, columnspan=2, sticky="w", pady=(10,0))

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=8, column=0, columnspan=3, sticky="e", pady=(12,0))
        ttk.Button(btn_frame, text="Guardar", command=self.save).grid(row=0, column=0, padx=(0,6))
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).grid(row=0, column=1)

        self.selected_tag_ids = []
        self._load_all_tags()

        if self.action:
            self.desc_entry.insert(0, self.action["description"])
            self.status_var.set(bool(self.action["is_complete"]))
            current = get_action_tags(self.action["id"])
            for t in current:
                self.selected_tags_list.insert(tk.END, t["name"])
                self.selected_tag_ids.append(t["id"])
            self._refresh_results()

    def _load_all_tags(self):
        self.all_tags = list_all_tags()
        self._refresh_results()

    def _refresh_results(self):
        term = (self.search_var.get() or "").strip().lower()
        # Exclude ones already selected
        available = [t for t in self.all_tags if t["id"] not in self.selected_tag_ids]
        if term:
            available = [t for t in available if term in t["name"].lower()]
        self.filtered_available = available
        self.available_list.delete(0, tk.END)
        for t in self.filtered_available:
            self.available_list.insert(tk.END, t["name"])

    def add_selected_from_results(self, first_only=False):
        # Choose selected in available_list or first item if first_only
        idx = None
        if first_only:
            if self.filtered_available:
                idx = 0
        else:
            sel = self.available_list.curselection()
            if sel:
                idx = sel[0]
        if idx is None:
            return
        t = self.filtered_available[idx]
        if t["id"] in self.selected_tag_ids:
            return
        self.selected_tag_ids.append(t["id"])
        self.selected_tags_list.insert(tk.END, t["name"])
        self._refresh_results()

    def create_new_tag(self):
        name = simpledialog.askstring("Nueva etiqueta", "Nombre de la etiqueta:", parent=self)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        try:
            create_tag(name)
            if self.refresh_tags_cb:
                self.refresh_tags_cb()
            self._load_all_tags()
            # Pre-cargar búsqueda con el nombre recién creado
            self.search_var.set(name)
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", f"Ya existe la etiqueta '{name}'.")

    def remove_selected_tag(self):
        idx = self.selected_tags_list.curselection()
        if not idx:
            return
        self.selected_tags_list.delete(idx[0])
        del self.selected_tag_ids[idx[0]]
        self._refresh_results()

    def save(self):
        desc = self.desc_entry.get().strip()
        if not desc:
            messagebox.showinfo("Info", "La descripción no puede estar vacía.")
            return
        if self.action:
            update_action(self.action["id"], desc, self.selected_tag_ids, is_complete=self.status_var.get())
        else:
            create_action(self.project_id, desc, self.selected_tag_ids)
        if self.on_save:
            self.on_save()
        self.destroy()


class NextActionDialog(tk.Toplevel):
    def __init__(self, master, action_row, tags_for_action, focus_project_cb, mark_done_cb):
        super().__init__(master)
        self.title("Siguiente acción")
        self.geometry("520x240")
        self.configure(padx=12, pady=12)

        ttk.Label(self, text="Proyecto:", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(self, text=action_row["project_name"]).grid(row=0, column=1, sticky="w")

        ttk.Label(self, text="Acción:", font=("TkDefaultFont", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(6,0))
        ttk.Label(self, text=action_row["description"], wraplength=380).grid(row=1, column=1, sticky="w", pady=(6,0))

        ttk.Label(self, text="Etiquetas:", font=("TkDefaultFont", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(6,0))
        ttk.Label(self, text=", ".join(tags_for_action)).grid(row=2, column=1, sticky="w", pady=(6,0))

        btnf = ttk.Frame(self)
        btnf.grid(row=3, column=0, columnspan=2, sticky="e", pady=(16,0))
        ttk.Button(btnf, text="Marcar como completada", command=lambda: (mark_done_cb(action_row["id"]), self._close())).grid(row=0, column=0, padx=(0,8))
        ttk.Button(btnf, text="Ir al proyecto", command=lambda: (focus_project_cb(action_row["project_id"], action_row["id"]), self._close())).grid(row=0, column=1)
        ttk.Button(btnf, text="Cerrar", command=self._close).grid(row=0, column=2, padx=(8,0))

    def _close(self):
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x640")
        self.minsize(980, 560)

        self._build_main_area()
        self._load_projects()
        self._refresh_filter_tags()

    def _build_main_area(self):
        main = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main, padding=(10,10))
        main.add(left, weight=1)

        ttk.Label(left, text="Proyectos").pack(anchor="w")
        self.projects_list = tk.Listbox(left, height=12, exportselection=False)
        self.projects_list.pack(fill=tk.BOTH, expand=True, pady=(4,6))
        self.projects_list.bind("<<ListboxSelect>>", self._on_project_selected)

        proj_btns = ttk.Frame(left)
        proj_btns.pack(fill=tk.X, pady=(0,6))
        ttk.Button(proj_btns, text="Agregar proyecto", command=self._add_project).pack(side=tk.LEFT)
        ttk.Button(proj_btns, text="Renombrar", command=self._rename_project).pack(side=tk.LEFT, padx=(6,0))
        ttk.Button(proj_btns, text="Eliminar", command=self._delete_project).pack(side=tk.LEFT, padx=(6,0))

        center = ttk.Frame(main, padding=(10,10))
        main.add(center, weight=3)

        ttk.Label(center, text="Acciones del proyecto seleccionado").pack(anchor="w")
        columns = ("id", "descripcion", "tags", "estado", "creada")
        self.actions_tree = ttk.Treeview(center, columns=columns, show="headings", height=16)
        self.actions_tree.heading("id", text="ID")
        self.actions_tree.heading("descripcion", text="Descripción")
        self.actions_tree.heading("tags", text="Etiquetas")
        self.actions_tree.heading("estado", text="Estado")
        self.actions_tree.heading("creada", text="Creada")
        self.actions_tree.column("id", width=40, anchor="center")
        self.actions_tree.column("descripcion", width=360)
        self.actions_tree.column("tags", width=240)
        self.actions_tree.column("estado", width=100, anchor="center")
        self.actions_tree.column("creada", width=180, anchor="center")
        self.actions_tree.pack(fill=tk.BOTH, expand=True, pady=(4,6))

        self.actions_tree.bind("<Double-1>", self._edit_selected_action)

        act_btns = ttk.Frame(center)
        act_btns.pack(fill=tk.X)
        ttk.Button(act_btns, text="Agregar acción", command=self._add_action).pack(side=tk.LEFT)
        ttk.Button(act_btns, text="Editar", command=self._edit_selected_action).pack(side=tk.LEFT, padx=(6,0))
        ttk.Button(act_btns, text="Alternar completa", command=self._toggle_selected_action).pack(side=tk.LEFT, padx=(6,0))
        ttk.Button(act_btns, text="Eliminar", command=self._delete_selected_action).pack(side=tk.LEFT, padx=(6,0))

        right = ttk.Frame(main, padding=(10,10))
        main.add(right, weight=1)

        ttk.Label(right, text="Filtrar por etiquetas").pack(anchor="w")

        list_frame = ttk.Frame(right)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(4,6))

        self.filter_tags_list = tk.Listbox(list_frame, selectmode=tk.EXTENDED, exportselection=False)
        vscroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.filter_tags_list.yview)
        self.filter_tags_list.configure(yscrollcommand=vscroll.set)

        self.filter_tags_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(right, text="Siguiente acción", command=self._show_next_action).pack(fill=tk.X, pady=(6,4))
        ttk.Button(right, text="Gestionar etiquetas…", command=self._open_tag_manager).pack(fill=tk.X)

    def _refresh_filter_tags(self):
        selected_names = [self.filter_tags_list.get(i) for i in self.filter_tags_list.curselection()]
        self.filter_tags_list.delete(0, tk.END)
        self.all_tags = list_all_tags()
        for t in self.all_tags:
            self.filter_tags_list.insert(tk.END, t["name"])
        to_select = []
        for i, t in enumerate(self.all_tags):
            if t["name"] in selected_names:
                to_select.append(i)
        for i in to_select:
            self.filter_tags_list.selection_set(i)

    def _get_selected_filter_tag_ids(self):
        indices = self.filter_tags_list.curselection()
        ids = []
        for i in indices:
            ids.append(self.all_tags[i]["id"])
        return ids

    def _show_next_action(self):
        tag_ids = self._get_selected_filter_tag_ids()
        row = find_next_action_by_tags(tag_ids)
        if not row:
            messagebox.showinfo("Sin resultados", "No hay acciones pendientes que coincidan con las etiquetas seleccionadas.")
            return
        tags = [t["name"] for t in get_action_tags(row["id"])]
        NextActionDialog(
            self,
            row,
            tags,
            focus_project_cb=self._focus_project_and_action,
            mark_done_cb=self._mark_action_done_and_refresh,
        )

    def _open_tag_manager(self):
        TagManager(self, on_close=self._refresh_after_tag_manager)

    def _refresh_after_tag_manager(self):
        self._refresh_filter_tags()
        self._reload_actions_for_current_project()

    def _mark_action_done_and_refresh(self, action_id):
        toggle_action_status(action_id)
        self._reload_actions_for_current_project()

    def _focus_project_and_action(self, project_id, action_id):
        target_index = None
        for idx, p in enumerate(self._projects_cache):
            if p["id"] == project_id:
                target_index = idx
                break
        if target_index is not None:
            self.projects_list.selection_clear(0, tk.END)
            self.projects_list.selection_set(target_index)
            self.projects_list.see(target_index)
            self._on_project_selected(None)
            for iid in self.actions_tree.get_children():
                if self.actions_tree.set(iid, "id") == str(action_id):
                    self.actions_tree.selection_set(iid)
                    self.actions_tree.see(iid)
                    break

    def _load_projects(self):
        self.projects_list.delete(0, tk.END)
        self._projects_cache = list_projects()
        for p in self._projects_cache:
            self.projects_list.insert(tk.END, p["name"])
        if self._projects_cache:
            self.projects_list.selection_set(0)
            self._on_project_selected(None)

    def _get_selected_project(self):
        idxs = self.projects_list.curselection()
        if not idxs:
            return None
        return self._projects_cache[idxs[0]]

    def _on_project_selected(self, event):
        self._reload_actions_for_current_project()

    def _reload_actions_for_current_project(self):
        p = self._get_selected_project()
        self.actions_tree.delete(*self.actions_tree.get_children())
        if not p:
            return
        actions = list_actions(p["id"])
        for a in actions:
            tag_names = [t["name"] for t in get_action_tags(a["id"])]
            estado = "Completada" if a["is_complete"] else "Pendiente"
            self.actions_tree.insert("", tk.END, values=(a["id"], a["description"], ", ".join(tag_names), estado, a["created_at"]))

    def _add_project(self):
        name = simpledialog.askstring("Nuevo proyecto", "Nombre del proyecto:", parent=self)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        try:
            create_project(name)
            self._load_projects()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", f"Ya existe un proyecto llamado '{name}'.")

    def _rename_project(self):
        p = self._get_selected_project()
        if not p:
            messagebox.showinfo("Info", "Selecciona un proyecto para renombrar.")
            return
        new_name = simpledialog.askstring("Renombrar proyecto", "Nuevo nombre:", initialvalue=p["name"], parent=self)
        if not new_name:
            return
        new_name = new_name.strip()
        if not new_name:
            return
        try:
            update_project(p["id"], new_name)
            self._load_projects()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", f"Ya existe un proyecto llamado '{new_name}'.")

    def _delete_project(self):
        p = self._get_selected_project()
        if not p:
            messagebox.showinfo("Info", "Selecciona un proyecto para eliminar.")
            return
        if messagebox.askyesno("Confirmar", f"¿Eliminar el proyecto '{p['name']}' y todas sus acciones?"):
            delete_project(p["id"])
            self._load_projects()

    def _get_selected_action_id(self):
        sel = self.actions_tree.selection()
        if not sel:
            return None
        values = self.actions_tree.item(sel[0], "values")
        return int(values[0])

    def _add_action(self):
        p = self._get_selected_project()
        if not p:
            messagebox.showinfo("Info", "Primero crea o selecciona un proyecto.")
            return
        ActionEditor(self, p["id"], action=None, on_save=self._reload_actions_for_current_project, refresh_tags_cb=self._refresh_filter_tags)

    def _edit_selected_action(self, event=None):
        p = self._get_selected_project()
        if not p:
            return
        aid = self._get_selected_action_id()
        if not aid:
            messagebox.showinfo("Info", "Selecciona una acción para editar.")
            return
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM actions WHERE id=?", (aid,))
        action_row = cur.fetchone()
        conn.close()
        if not action_row:
            return
        ActionEditor(self, p["id"], action=action_row, on_save=self._reload_actions_for_current_project, refresh_tags_cb=self._refresh_filter_tags)

    def _toggle_selected_action(self):
        aid = self._get_selected_action_id()
        if not aid:
            messagebox.showinfo("Info", "Selecciona una acción para alternar su estado.")
            return
        toggle_action_status(aid)
        self._reload_actions_for_current_project()

    def _delete_selected_action(self):
        aid = self._get_selected_action_id()
        if not aid:
            messagebox.showinfo("Info", "Selecciona una acción para eliminar.")
            return
        if messagebox.askyesno("Confirmar", "¿Eliminar esta acción?"):
            delete_action(aid)
            self._reload_actions_for_current_project()


def main():
    ensure_db_location()
    init_db()
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
