import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
from datetime import datetime
import hashlib

try:
    import pandas as pd
except ImportError:
    pd = None

# Dependências para Gráficos
try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    import matplotlib.pyplot as plt
    plt.style.use('ggplot')
except ImportError:
    FigureCanvasTkAgg = None 
    NavigationToolbar2Tk = None
    plt = None


# --- FUNÇÃO DE HASHING PARA SENHAS ---

def hash_password(password):
    """Gera um hash SHA256 para a senha com um salt simples."""
    # Usar um salt constante para simplificar a demonstração no ambiente Tkinter/SQLite
    salt = "loja_veiculos_salt"
    hashed = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    return hashed

# --- JANELA DE LOGIN ---

class LoginWindow:
    def __init__(self, master):
        self.master = master
        self.conn = sqlite3.connect('vehicle_management.db')
        self.cursor = self.conn.cursor()

        # Garante que as tabelas (incluindo 'users') e o Admin inicial existam
        self.setup_db()
        
        self.master.title("Login - Sistema de Gestão")
        self.master.geometry("600x600")
        self.master.resizable(False, False)

        # Configuração do Frame
        login_frame = ttk.Frame(master, padding="20")
        login_frame.pack(fill='both', expand=True)

        ttk.Label(login_frame, text="Acesso ao Sistema", font=("Arial", 16, "bold")).pack(pady=10)

        # Usuário
        ttk.Label(login_frame, text="Usuário:").pack(pady=5)
        self.username_entry = ttk.Entry(login_frame, width=30)
        self.username_entry.pack(pady=5)
        self.username_entry.insert(0, 'admin')

        # Senha
        ttk.Label(login_frame, text="Senha:").pack(pady=5)
        self.password_entry = ttk.Entry(login_frame, show="*", width=30)
        self.password_entry.pack(pady=5)
        self.password_entry.insert(0, 'admin')
        self.password_entry.bind('<Return>', lambda event: self.authenticate())

        # Botão de Login
        ttk.Button(login_frame, text="Login", command=self.authenticate).pack(pady=15)

    def setup_db(self):
        """Cria a tabela de usuários e insere o admin padrão."""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    role TEXT NOT NULL,
                    name TEXT
                )
            """)
            
            # Insere o Admin padrão se não existir
            admin_username = 'admin'
            admin_password_hash = hash_password('admin')
            
            self.cursor.execute("SELECT COUNT(*) FROM users WHERE username=?", (admin_username,))
            if self.cursor.fetchone()[0] == 0:
                self.cursor.execute(
                    "INSERT INTO users (username, hashed_password, role, name) VALUES (?, ?, ?, ?)",
                    (admin_username, admin_password_hash, 'Admin', 'Administrador Principal')
                )
                self.conn.commit()
                messagebox.showinfo("Configuração Inicial", "Perfil de Admin criado: user='admin', senha='admin'.")
            
        except sqlite3.Error as e:
            messagebox.showerror("Erro de DB", f"Falha ao criar tabela de usuários: {e}")


    def authenticate(self):
        """Tenta autenticar o usuário e abre a aplicação principal."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Erro de Login", "Preencha usuário e senha.")
            return

        hashed_input = hash_password(password)
        
        self.cursor.execute(
            "SELECT id, role, name, hashed_password FROM users WHERE username = ?", 
            (username,)
        )
        user_record = self.cursor.fetchone()

        if user_record and user_record[3] == hashed_input:
            user_id = user_record[0]
            role = user_record[1]
            user_name = user_record[2]
            
            self.master.destroy() 
            
            # Abre a aplicação principal
            root = tk.Tk()
            app = VehicleStoreApp(root, user_id, role, user_name)
            root.mainloop()

        else:
            messagebox.showerror("Erro de Login", "Usuário ou senha inválidos.")


# --- CLASSE PRINCIPAL DA APLICAÇÃO ---

class VehicleStoreApp:
    def __init__(self, master, user_id, role, user_name):
        """Inicializa a aplicação, configura o DB e a interface."""
        self.master = master
        self.current_user_id = user_id
        self.current_role = role
        self.current_user_name = user_name
        
        master.title(f"Sistema de Gestão de Vendas de Veículos - Logado como: {user_name} ({role})")
        master.geometry("1150x700")
        
        # --- Configuração do Banco de Dados SQLite ---
        self.conn = sqlite3.connect('vehicle_management.db')
        self.cursor = self.conn.cursor()
        self.create_tables() # Garante que as tabelas de dados existam

        # --- Variáveis de Estado ---
        self.report_type = tk.StringVar(value="Estoque")
        self.start_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-01")) 
        self.end_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d")) 
        self.stock_threshold_var = tk.StringVar(value="5")
        self.include_inactive_var = tk.IntVar()

        # --- Configuração da Interface com Abas (Notebook) ---
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(pady=10, padx=10, fill="both", expand=True)

        # Criação dos Frames das Abas
        self.params_frame = ttk.Frame(self.notebook, padding="10")
        self.seller_frame = ttk.Frame(self.notebook, padding="10")
        self.inventory_frame = ttk.Frame(self.notebook, padding="10")
        self.customer_frame = ttk.Frame(self.notebook, padding="10")
        self.sales_frame = ttk.Frame(self.notebook, padding="10")
        self.reports_frame = ttk.Frame(self.notebook, padding="10") 
        self.analytics_frame = ttk.Frame(self.notebook, padding="10")
        self.admin_frame = ttk.Frame(self.notebook, padding="10") # NOVA ABA ADMIN

        # Adiciona as Abas
        self.notebook.add(self.params_frame, text="1. Parâmetros (Marcas/Modelos)")
        self.notebook.add(self.seller_frame, text="2. Cadastro de Vendedores")
        self.notebook.add(self.inventory_frame, text="3. Estoque (Veículos)")
        self.notebook.add(self.customer_frame, text="4. Cadastro de Clientes")
        self.notebook.add(self.sales_frame, text="5. Gestão de Vendas")
        self.notebook.add(self.reports_frame, text="6. Relatórios") 
        self.notebook.add(self.analytics_frame, text="7. Análise Gráfica")

        # Adiciona a aba de Admin SOMENTE se o usuário for 'Admin'
        if self.current_role == 'Admin':
            self.notebook.add(self.admin_frame, text="8. Gestão de Usuários (Admin)")
        
        # Constrói o conteúdo de cada aba
        self.setup_parameters_tab(self.params_frame)
        self.setup_seller_tab(self.seller_frame)
        self.setup_inventory_tab(self.inventory_frame)
        self.setup_customer_tab(self.customer_frame)
        self.setup_sales_tab(self.sales_frame)
        self.setup_reports_tab(self.reports_frame)
        self.setup_analytics_tab(self.analytics_frame)
        if self.current_role == 'Admin':
            self.setup_admin_tab(self.admin_frame)
        
        # Inicializa e recarrega dados ao trocar de aba
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.load_initial_data()
        
        # Botão de Logout
        ttk.Button(master, text="Logout", command=self.logout).pack(pady=5, padx=10, side=tk.RIGHT)

    def logout(self):
        """Fecha a aplicação atual e retorna para a tela de login."""
        self.master.destroy()
        # Abre a tela de login novamente
        root = tk.Tk()
        LoginWindow(root)
        root.mainloop()

    def create_tables(self):
        """Cria todas as tabelas necessárias no SQLite. (Tabela users é criada no LoginWindow)"""
        try:
            # 1. Tabela de Parâmetros (Marcas)
            self.cursor.execute("CREATE TABLE IF NOT EXISTS makes (name TEXT PRIMARY KEY)")
            # 2. Tabela de Parâmetros (Modelos)
            self.cursor.execute("CREATE TABLE IF NOT EXISTS models (id INTEGER PRIMARY KEY, make_name TEXT, model_name TEXT, UNIQUE(make_name, model_name))")
            # 3. Tabela de Vendedores
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS sellers (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT,
                    email TEXT UNIQUE,
                    is_active INTEGER DEFAULT 1
                )
            """)
            # 4. Tabela de Veículos em Estoque 
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY,
                    make TEXT NOT NULL,
                    model TEXT NOT NULL,
                    manufacture_year INTEGER,
                    model_year INTEGER,
                    color TEXT,
                    sale_price REAL NOT NULL,
                    stock INTEGER NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    sale_date_only TEXT
                )
            """)
            # 5. Tabela de Clientes
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT,
                    email TEXT UNIQUE,
                    is_active INTEGER DEFAULT 1
                )
            """)
            # 6. Tabela de Histórico de Vendas
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY,
                    vehicle_id INTEGER,
                    vehicle_info TEXT,
                    customer_name TEXT,
                    seller_name TEXT,
                    final_price REAL NOT NULL,
                    sale_date TEXT NOT NULL
                )
            """)
            
            # Checagem e adição da nova coluna 'sale_date_only' se não existir (para compatibilidade com DBs antigos)
            self.cursor.execute("PRAGMA table_info(vehicles)")
            columns = [col[1] for col in self.cursor.fetchall()]
            if 'sale_date_only' not in columns:
                 self.cursor.execute("ALTER TABLE vehicles ADD COLUMN sale_date_only TEXT")
            
            self.conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Falha ao criar tabelas: {e}")

    def load_initial_data(self):
        """Carrega dados iniciais ao iniciar o app."""
        self.refresh_inventory_list()
        self.refresh_customer_list()
        self.refresh_seller_list()
        self.refresh_sales_history()
        self.refresh_param_lists()
        self.refresh_sales_dropdowns()

    def on_tab_change(self, event):
        """Ação executada ao trocar de aba."""
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        
        if "Parâmetros" in selected_tab:
            self.refresh_param_lists()
        elif "Vendedores" in selected_tab:
            self.refresh_seller_list()
        elif "Estoque" in selected_tab:
            self.refresh_inventory_list()
            self.refresh_param_dropdowns()
        elif "Clientes" in selected_tab:
            self.refresh_customer_list()
        elif "Vendas" in selected_tab:
            self.refresh_sales_dropdowns()
            self.refresh_sales_history()
        elif "Relatórios" in selected_tab:
            self.toggle_report_filters(self.report_type.get())
        elif "Análise Gráfica" in selected_tab:
            self.plot_analytics()
        elif "Gestão de Usuários" in selected_tab and self.current_role == 'Admin':
            self.refresh_user_list() # NOVO: Recarrega lista de usuários

    # --- SETUP E LÓGICA DO MÓDULO 1: PARÂMETROS (Mantido) ---
    # ... (código refresh_param_lists, add_make, add_model, refresh_param_dropdowns, update_inv_model_dropdown, setup_parameters_tab)
    
    def refresh_param_lists(self):
        """Recarrega as Treeviews de Marcas e Modelos."""
        # Limpar Marcas
        for item in self.make_tree.get_children(): self.make_tree.delete(item)
        self.cursor.execute("SELECT name FROM makes ORDER BY name ASC")
        for row in self.cursor.fetchall():
            self.make_tree.insert("", tk.END, values=row)

        # Limpar Modelos
        for item in self.model_tree.get_children(): self.model_tree.delete(item)
        self.cursor.execute("SELECT make_name, model_name FROM models ORDER BY make_name, model_name ASC")
        for row in self.cursor.fetchall():
            self.model_tree.insert("", tk.END, values=row)
            
        self.refresh_param_dropdowns()

    def add_make(self):
        """Adiciona uma nova Marca."""
        make_name = self.make_entry.get().strip().title()
        if not make_name: return messagebox.showwarning("Atenção", "O campo Marca não pode estar vazio.")
        try:
            self.cursor.execute("INSERT INTO makes (name) VALUES (?)", (make_name,))
            self.conn.commit()
            self.make_entry.delete(0, tk.END)
            self.refresh_param_lists()
            messagebox.showinfo("Sucesso", f"Marca '{make_name}' adicionada.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", "Esta Marca já existe.")
        except sqlite3.Error as e:
            messagebox.showerror("Erro", f"Erro: {e}")

    def add_model(self):
        """Adiciona um novo Modelo, vinculado a uma Marca."""
        make_name = self.model_make_var.get()
        model_name = self.model_entry.get().strip().title()
        
        if make_name == "Selecione a Marca" or not model_name: return messagebox.showwarning("Atenção", "Selecione a Marca e digite o Modelo.")
        
        try:
            self.cursor.execute("INSERT INTO models (make_name, model_name) VALUES (?, ?)", (make_name, model_name))
            self.conn.commit()
            self.model_entry.delete(0, tk.END)
            self.refresh_param_lists()
            messagebox.showinfo("Sucesso", f"Modelo '{model_name}' adicionado para a Marca '{make_name}'.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", "Este Modelo já existe para esta Marca.")
        except sqlite3.Error as e:
            messagebox.showerror("Erro", f"Erro: {e}")

    def refresh_param_dropdowns(self):
        """Atualiza os OptionMenus de Marca e Modelo na aba Estoque."""
        self.cursor.execute("SELECT name FROM makes ORDER BY name ASC")
        makes = [row[0] for row in self.cursor.fetchall()]
        
        # Atualiza o dropdown na aba Parâmetros para cadastro de modelo
        menu = self.model_make_menu['menu']
        menu.delete(0, 'end')
        if makes:
            self.model_make_var.set(makes[0])
            for make in makes:
                menu.add_command(label=make, command=tk._setit(self.model_make_var, make))
        else:
            self.model_make_var.set("Selecione a Marca")

        # Atualiza o dropdown na aba Estoque
        menu_estoque = self.inv_make_menu['menu']
        menu_estoque.delete(0, 'end')
        if makes:
            self.inv_make_var.set(makes[0])
            for make in makes:
                menu_estoque.add_command(label=make, command=tk._setit(self.inv_make_var, make, self.update_inv_model_dropdown))
        else:
            self.inv_make_var.set("Selecione a Marca")
            self.inv_model_var.set("Selecione o Modelo")
            
        self.update_inv_model_dropdown()
        
    def update_inv_model_dropdown(self, *args):
        """Atualiza o dropdown de Modelos na aba Estoque baseado na Marca selecionada."""
        make_name = self.inv_make_var.get()
        
        menu = self.inv_model_menu['menu']
        menu.delete(0, 'end')
        self.inv_model_var.set("")
        
        if make_name and make_name != "Selecione a Marca":
            self.cursor.execute("SELECT model_name FROM models WHERE make_name = ? ORDER BY model_name ASC", (make_name,))
            models = [row[0] for row in self.cursor.fetchall()]
            
            if models:
                self.inv_model_var.set(models[0])
                for model in models:
                    menu.add_command(label=model, command=tk._setit(self.inv_model_var, model))
            else:
                self.inv_model_var.set("Nenhum Modelo Cadastrado")
        else:
            self.inv_model_var.set("Selecione o Modelo")

    def setup_parameters_tab(self, frame):
        """Configura a aba de Parâmetros (Marcas e Modelos)."""
        
        # Frame para Marcas
        make_frame = ttk.LabelFrame(frame, text="Cadastrar Nova Marca", padding="10")
        make_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nwe")
        ttk.Label(make_frame, text="Nome da Marca:").pack(pady=5)
        self.make_entry = ttk.Entry(make_frame, width=30)
        self.make_entry.pack(pady=5)
        ttk.Button(make_frame, text="Adicionar Marca", command=self.add_make).pack(pady=10)

        # Treeview de Marcas
        ttk.Label(frame, text="Marcas Cadastradas:", font=("Arial", 10, "bold")).grid(row=1, column=0, padx=5, pady=(15, 5), sticky='w')
        columns_make = ("Marca",)
        self.make_tree = ttk.Treeview(frame, columns=columns_make, show='headings', height=10)
        self.make_tree.heading("Marca", text="Marca")
        self.make_tree.column("Marca", width=250, anchor='w')
        self.make_tree.grid(row=2, column=0, padx=5, pady=5, sticky="nwe")
        
        # Frame para Modelos
        model_frame = ttk.LabelFrame(frame, text="Cadastrar Novo Modelo", padding="10")
        model_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nwe")

        ttk.Label(model_frame, text="Selecione a Marca:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.model_make_var = tk.StringVar(value="Selecione a Marca")
        self.model_make_menu = ttk.OptionMenu(model_frame, self.model_make_var, self.model_make_var.get())
        self.model_make_menu.config(width=25)
        self.model_make_menu.grid(row=0, column=1, padx=5, pady=5, sticky='we')
        
        ttk.Label(model_frame, text="Nome do Modelo:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.model_entry = ttk.Entry(model_frame, width=30)
        self.model_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(model_frame, text="Adicionar Modelo", command=self.add_model).grid(row=2, column=0, columnspan=2, pady=10, sticky='we')
        
        # Treeview de Modelos
        ttk.Label(frame, text="Modelos Cadastrados:", font=("Arial", 10, "bold")).grid(row=1, column=1, padx=5, pady=(15, 5), sticky='w')
        columns_model = ("Marca", "Modelo")
        self.model_tree = ttk.Treeview(frame, columns=columns_model, show='headings', height=10)
        self.model_tree.heading("Marca", text="Marca")
        self.model_tree.column("Marca", width=150, anchor='w')
        self.model_tree.heading("Modelo", text="Modelo")
        self.model_tree.column("Modelo", width=150, anchor='w')
        self.model_tree.grid(row=2, column=1, padx=5, pady=5, sticky="nwe")


    # --- SETUP E LÓGICA DO MÓDULO 2: CADASTRO DE VENDEDORES (Mantido) ---

    def refresh_seller_list(self):
        """Limpa e recarrega a Treeview de Vendedores."""
        for item in self.seller_tree.get_children(): self.seller_tree.delete(item)

        # Query para incluir is_active
        self.cursor.execute("SELECT id, name, phone, email, is_active FROM sellers ORDER BY name ASC")
        sellers = self.cursor.fetchall()
        for seller in sellers:
            sid, name, phone, email, is_active = seller
            status = "Ativo" if is_active else "Inativo"
            tag = 'inactive' if not is_active else ''
            self.seller_tree.insert("", tk.END, values=(sid, name, phone, email, status), tags=(tag,))

    def add_seller(self):
        """Adiciona um novo vendedor (ativo por padrão)."""
        name = self.seller_name_entry.get().strip().title()
        phone = self.seller_phone_entry.get().strip()
        email = self.seller_email_entry.get().strip()

        if not name or not email: return messagebox.showwarning("Atenção", "Nome e Email são obrigatórios para o Vendedor.")
        
        try:
            # is_active usa o valor default 1 (Ativo)
            self.cursor.execute(
                "INSERT INTO sellers (name, phone, email) VALUES (?, ?, ?)", 
                (name, phone, email)
            )
            self.conn.commit()
            messagebox.showinfo("Sucesso", f"Vendedor '{name}' cadastrado.")
            self.seller_name_entry.delete(0, tk.END)
            self.seller_phone_entry.delete(0, tk.END)
            self.seller_email_entry.delete(0, tk.END)
            self.refresh_seller_list()
            self.refresh_sales_dropdowns() # Recarrega dropdown de vendas
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", "Email já cadastrado para outro Vendedor.")
        except sqlite3.Error as e:
            messagebox.showerror("Erro", f"Erro: {e}")

    def toggle_seller_status(self):
        """Ativa/Inativa o vendedor selecionado."""
        selected_item = self.seller_tree.focus()
        if not selected_item:
            return messagebox.showwarning("Atenção", "Selecione um vendedor na lista.")

        values = self.seller_tree.item(selected_item, 'values')
        seller_id = values[0]
        current_status = values[4]
        new_status = 0 if current_status == "Ativo" else 1
        new_status_text = "Inativo" if new_status == 0 else "Ativo"
        
        confirmation = messagebox.askyesno(
            "Confirmação de Status",
            f"Deseja realmente mudar o status do vendedor '{values[1]}' para '{new_status_text}'?"
        )

        if confirmation:
            try:
                self.cursor.execute("UPDATE sellers SET is_active = ? WHERE id = ?", (new_status, seller_id))
                self.conn.commit()
                messagebox.showinfo("Sucesso", f"Status do vendedor atualizado para {new_status_text}.")
                self.refresh_seller_list()
                self.refresh_sales_dropdowns() # Atualiza dropdown de vendas
            except sqlite3.Error as e:
                messagebox.showerror("Erro", f"Erro ao atualizar status: {e}")


    def setup_seller_tab(self, frame):
        """Configura a aba de Cadastro de Vendedores."""
        
        # Inputs para Cadastrar Vendedor
        input_frame = ttk.LabelFrame(frame, text="Cadastrar Novo Vendedor", padding="10")
        input_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(input_frame, text="Nome:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.seller_name_entry = ttk.Entry(input_frame, width=30)
        self.seller_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Label(input_frame, text="Telefone:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.seller_phone_entry = ttk.Entry(input_frame, width=30)
        self.seller_phone_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(input_frame, text="Email:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.seller_email_entry = ttk.Entry(input_frame, width=30)
        self.seller_email_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Button(input_frame, text="Cadastrar Vendedor", command=self.add_seller).grid(row=3, column=0, columnspan=2, pady=10, sticky='we')
        
        # Visualização de Vendedores (Treeview)
        ttk.Label(frame, text="Vendedores Cadastrados:", font=("Arial", 12)).pack(pady=(15, 5), anchor='w')

        # Colunas
        columns = ("ID", "Nome", "Telefone", "Email", "Status")
        self.seller_tree = ttk.Treeview(frame, columns=columns, show='headings')
        self.seller_tree.pack(fill='both', expand=True, padx=5, pady=5)

        for col in columns:
            self.seller_tree.heading(col, text=col)
        
        self.seller_tree.column("ID", width=40)
        self.seller_tree.column("Nome", width=180, anchor='w')
        self.seller_tree.column("Telefone", width=100, anchor='center')
        self.seller_tree.column("Email", width=250, anchor='w')
        self.seller_tree.column("Status", width=80, anchor='center')

        # Estilo para inativos
        self.seller_tree.tag_configure('inactive', background='#f0f0f0', foreground='#999999')

        tree_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.seller_tree.yview)
        tree_scroll.pack(side='right', fill='y')
        self.seller_tree.configure(yscrollcommand=tree_scroll.set)
        
        # Botão para Ativar/Inativar Vendedor
        ttk.Button(frame, text="Ativar / Inativar Vendedor Selecionado", command=self.toggle_seller_status).pack(pady=10)


    # --- SETUP E LÓGICA DO MÓDULO 3: ESTOQUE (Mantido) ---
    
    def get_stock_threshold(self):
        """Retorna o limite de estoque para filtros."""
        try:
            threshold_str = self.stock_threshold_var.get().strip()
            return int(threshold_str) if threshold_str else 9999999
        except ValueError:
            messagebox.showerror("Erro de Filtro", "O limite de estoque deve ser um número inteiro positivo.")
            return None
            
    def refresh_inventory_list(self):
        """Limpa e recarrega a Treeview do estoque com os dados mais recentes."""
        for item in self.inventory_tree.get_children(): self.inventory_tree.delete(item)

        # Consulta ALTERADA para incluir is_active e sale_date_only
        self.cursor.execute("SELECT id, make, model, manufacture_year, model_year, color, sale_price, stock, is_active, sale_date_only FROM vehicles ORDER BY is_active DESC, make, model ASC")
        vehicles = self.cursor.fetchall()
        for vehicle in vehicles:
            # Desempacota os novos campos
            vid, make, model, manuf_year, model_year, color, price, stock, is_active, sale_date = vehicle
            price_formatted = f"R$ {price:.2f}"
            
            # ATUALIZADO: Renomeia o status
            if is_active:
                status = "Disponível" 
                display_sale_date = ""
            else:
                status = "Vendido"
                display_sale_date = sale_date if sale_date else "N/A"
            
            # Tags para cor
            tag = 'low_stock' if stock < self.get_stock_threshold() and is_active else 'inactive' if not is_active else ''
            
            # Valores ATUALIZADOS com Status e Data Venda
            self.inventory_tree.insert(
                "", 
                tk.END, 
                values=(vid, make, model, manuf_year, model_year, color, price_formatted, stock, status, display_sale_date), 
                tags=(tag,)
            )

    def add_vehicle(self):
        """Adiciona um novo veículo ao estoque (ativo por padrão)."""
        make = self.inv_make_var.get()
        model = self.inv_model_var.get()
        
        # Novos campos de Ano
        manuf_year_str = self.inv_manuf_year_entry.get().strip()
        model_year_str = self.inv_model_year_entry.get().strip()
        
        color = self.inv_color_var.get() # Variável do dropdown de cor
        price_str = self.inv_price_entry.get().strip()
        stock_str = self.inv_stock_entry.get().strip()

        if make == "Selecione a Marca" or model == "Selecione o Modelo" or not manuf_year_str or not model_year_str or not price_str or not stock_str:
            return messagebox.showwarning("Atenção", "Preencha todos os campos e selecione Marca/Modelo.")

        try:
            manuf_year = int(manuf_year_str)
            model_year = int(model_year_str)
            price = float(price_str.replace(',', '.'))
            stock = int(stock_str)
            current_year = datetime.now().year
            
            # Validação dos anos e outros campos
            if manuf_year < 1900 or manuf_year > current_year + 1 or model_year < 1900 or model_year > current_year + 1 or price <= 0 or stock < 0:
                 raise ValueError("Dados inválidos.")
                 
            if manuf_year > model_year:
                 return messagebox.showerror("Erro de Entrada", "O Ano de Fabricação não pode ser maior que o Ano Modelo.")
                 
        except ValueError:
            return messagebox.showerror("Erro de Entrada", "Anos, Preço e Estoque devem ser números válidos.")
            
        try:
            # INSERT ATUALIZADO (is_active usa default 1, sale_date_only é NULL)
            self.cursor.execute(
                "INSERT INTO vehicles (make, model, manufacture_year, model_year, color, sale_price, stock) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                (make, model, manuf_year, model_year, color, price, stock)
            )
            self.conn.commit()
            messagebox.showinfo("Sucesso", f"Veículo {make} {model}/{model_year} adicionado ao estoque.")
            # Limpa os novos campos
            self.inv_manuf_year_entry.delete(0, tk.END)
            self.inv_model_year_entry.delete(0, tk.END)
            
            self.inv_price_entry.delete(0, tk.END)
            self.inv_stock_entry.delete(0, tk.END)
            self.refresh_inventory_list()
        except sqlite3.Error as e:
            messagebox.showerror("Erro", f"Erro ao adicionar veículo: {e}")

    def toggle_vehicle_status(self):
        """Ativa/Inativa o veículo selecionado."""
        selected_item = self.inventory_tree.focus()
        if not selected_item:
            return messagebox.showwarning("Atenção", "Selecione um veículo na lista.")

        values = self.inventory_tree.item(selected_item, 'values')
        vehicle_id = values[0]
        current_status_text = values[8]
        
        # Determina o novo status e a ação na data de venda
        if current_status_text == "Disponível": # Ativo -> Inativo (Vendido, mas manualmente)
            new_status = 0
            new_status_text = "Vendido"
            # Define a data de venda como hoje se o estoque estiver zerado ou for inativado manualmente
            sale_date = datetime.now().strftime("%Y-%m-%d")
            
            confirmation = messagebox.askyesno(
                "Confirmação de Inativação",
                f"Deseja realmente marcar o veículo '{values[1]} {values[2]}' como VENDIDO e inativo?"
            )
            
        else: # Inativo/Vendido -> Ativo (Disponível)
            new_status = 1
            new_status_text = "Disponível"
            sale_date = None # Limpa a data de venda ao reativar

            confirmation = messagebox.askyesno(
                "Confirmação de Ativação",
                f"Deseja realmente marcar o veículo '{values[1]} {values[2]}' como DISPONÍVEL e ativo?"
            )

        if confirmation:
            try:
                # Se for ativado (Disponível), garante que o estoque > 0.
                if new_status == 1:
                    self.cursor.execute("SELECT stock FROM vehicles WHERE id = ?", (vehicle_id,))
                    current_stock = self.cursor.fetchone()[0]
                    if current_stock == 0:
                        return messagebox.showwarning("Atenção", "Não é possível reativar um veículo com Estoque 0. Ajuste o estoque antes.")
                
                # Atualiza o status e a data de venda/limpa a data de venda
                self.cursor.execute("UPDATE vehicles SET is_active = ?, sale_date_only = ? WHERE id = ?", (new_status, sale_date, vehicle_id))
                self.conn.commit()
                messagebox.showinfo("Sucesso", f"Status do veículo atualizado para {new_status_text}.")
                self.refresh_inventory_list()
                self.refresh_sales_dropdowns() # Atualiza dropdown de vendas
            except sqlite3.Error as e:
                messagebox.showerror("Erro", f"Erro ao atualizar status: {e}")

    def setup_inventory_tab(self, frame):
        """Configura a aba de Estoque (Veículos)."""
        
        # Cores predefinidas para o dropdown
        self.colors = ["Preto", "Branco", "Prata", "Vermelho", "Azul", "Cinza", "Verde", "Amarelo"]
        
        # Inputs para Adicionar Veículo
        input_frame = ttk.LabelFrame(frame, text="Adicionar Veículo ao Estoque", padding="10")
        input_frame.pack(fill='x', padx=5, pady=5)
        
        # Variáveis
        self.inv_make_var = tk.StringVar(value="Selecione a Marca")
        self.inv_model_var = tk.StringVar(value="Selecione o Modelo")
        self.inv_color_var = tk.StringVar(value=self.colors[0] if self.colors else "")

        # Linha 0: Marca e Modelo
        ttk.Label(input_frame, text="Marca:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.inv_make_menu = ttk.OptionMenu(input_frame, self.inv_make_var, self.inv_make_var.get())
        self.inv_make_menu.config(width=20)
        self.inv_make_menu.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(input_frame, text="Modelo:").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.inv_model_menu = ttk.OptionMenu(input_frame, self.inv_model_var, self.inv_model_var.get())
        self.inv_model_menu.config(width=20)
        self.inv_model_menu.grid(row=0, column=3, padx=5, pady=5, sticky='w')

        # Linha 1: Ano Fabricação e Ano Modelo
        ttk.Label(input_frame, text="Ano Fab.:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.inv_manuf_year_entry = ttk.Entry(input_frame, width=10)
        self.inv_manuf_year_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(input_frame, text="Ano Mod.:").grid(row=1, column=2, padx=5, pady=5, sticky='w')
        self.inv_model_year_entry = ttk.Entry(input_frame, width=10)
        self.inv_model_year_entry.grid(row=1, column=3, padx=5, pady=5, sticky='w')
        
        # Linha 2: Cor e Preço
        ttk.Label(input_frame, text="Cor:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        # Menu Suspenso de Cores
        self.inv_color_menu = ttk.OptionMenu(input_frame, self.inv_color_var, self.inv_color_var.get(), *self.colors)
        self.inv_color_menu.config(width=15)
        self.inv_color_menu.grid(row=2, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(input_frame, text="Preço Venda (R$):").grid(row=2, column=2, padx=5, pady=5, sticky='w')
        self.inv_price_entry = ttk.Entry(input_frame, width=15)
        self.inv_price_entry.grid(row=2, column=3, padx=5, pady=5, sticky='w')

        # Linha 3: Estoque
        ttk.Label(input_frame, text="Estoque (Qtde):").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        self.inv_stock_entry = ttk.Entry(input_frame, width=10)
        self.inv_stock_entry.grid(row=3, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Button(input_frame, text="Adicionar Veículo ao Estoque", command=self.add_vehicle).grid(row=4, column=0, columnspan=4, pady=10, sticky='we')
        
        # Visualização do Estoque (Treeview) - ATUALIZADO
        ttk.Label(frame, text="Estoque Atual de Veículos:", font=("Arial", 12)).pack(pady=(15, 5), anchor='w')

        # Colunas ATUALIZADAS (Adicionado Data Venda e Status renomeado)
        columns = ("ID", "Marca", "Modelo", "Ano Fab.", "Ano Mod.", "Cor", "Preço", "Estoque", "Status", "Data Venda")
        self.inventory_tree = ttk.Treeview(frame, columns=columns, show='headings')
        self.inventory_tree.pack(fill='both', expand=True, padx=5, pady=5)

        for col in columns:
            self.inventory_tree.heading(col, text=col.replace("Preço", "Preço (R$)"))
            self.inventory_tree.column(col, anchor='center')
        
        self.inventory_tree.column("ID", width=30)
        self.inventory_tree.column("Marca", width=70, anchor='w')
        self.inventory_tree.column("Modelo", width=100, anchor='w')
        self.inventory_tree.column("Ano Fab.", width=55)
        self.inventory_tree.column("Ano Mod.", width=55)
        self.inventory_tree.column("Cor", width=70)
        self.inventory_tree.column("Preço", width=90, anchor='e')
        self.inventory_tree.column("Estoque", width=60)
        self.inventory_tree.column("Status", width=70) 
        self.inventory_tree.column("Data Venda", width=80) # NOVA COLUNA
        
        # Estilização para inativos e estoque baixo
        self.inventory_tree.tag_configure('low_stock', background='#ffdddd', foreground='red')
        self.inventory_tree.tag_configure('inactive', background='#f0f0f0', foreground='#999999')

        tree_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.inventory_tree.yview)
        tree_scroll.pack(side='right', fill='y')
        self.inventory_tree.configure(yscrollcommand=tree_scroll.set)
        
        # Botão para Ativar/Inativar Veículo (agora Ativa/Marca como Vendido)
        ttk.Button(frame, text="Alterar Status do Veículo Selecionado", command=self.toggle_vehicle_status).pack(pady=10)


    # --- SETUP E LÓGICA DO MÓDULO 4: CLIENTES (Mantido) ---
    
    def refresh_customer_list(self):
        """Limpa e recarrega a Treeview de Clientes."""
        for item in self.customer_tree.get_children(): self.customer_tree.delete(item)

        # Query para incluir is_active
        self.cursor.execute("SELECT id, name, phone, email, is_active FROM customers ORDER BY name ASC")
        customers = self.cursor.fetchall()
        for customer in customers:
            cid, name, phone, email, is_active = customer
            status = "Ativo" if is_active else "Inativo"
            tag = 'inactive' if not is_active else ''
            self.customer_tree.insert("", tk.END, values=(cid, name, phone, email, status), tags=(tag,))

    def add_customer(self):
        """Adiciona um novo cliente (ativo por padrão)."""
        name = self.cust_name_entry.get().strip().title()
        phone = self.cust_phone_entry.get().strip()
        email = self.cust_email_entry.get().strip()

        if not name or not email: return messagebox.showwarning("Atenção", "Nome e Email são obrigatórios.")
        
        try:
            # is_active usa o valor default 1 (Ativo)
            self.cursor.execute(
                "INSERT INTO customers (name, phone, email) VALUES (?, ?, ?)", 
                (name, phone, email)
            )
            self.conn.commit()
            messagebox.showinfo("Sucesso", f"Cliente '{name}' cadastrado.")
            self.cust_name_entry.delete(0, tk.END)
            self.cust_phone_entry.delete(0, tk.END)
            self.cust_email_entry.delete(0, tk.END)
            self.refresh_customer_list()
            self.refresh_sales_dropdowns() # Recarrega dropdown de vendas
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", "Email já cadastrado.")
        except sqlite3.Error as e:
            messagebox.showerror("Erro", f"Erro: {e}")

    def toggle_customer_status(self):
        """Ativa/Inativa o cliente selecionado."""
        selected_item = self.customer_tree.focus()
        if not selected_item:
            return messagebox.showwarning("Atenção", "Selecione um cliente na lista.")

        values = self.customer_tree.item(selected_item, 'values')
        customer_id = values[0]
        current_status = values[4]
        new_status = 0 if current_status == "Ativo" else 1
        new_status_text = "Inativo" if new_status == 0 else "Ativo"
        
        confirmation = messagebox.askyesno(
            "Confirmação de Status",
            f"Deseja realmente mudar o status do cliente '{values[1]}' para '{new_status_text}'?"
        )

        if confirmation:
            try:
                self.cursor.execute("UPDATE customers SET is_active = ? WHERE id = ?", (new_status, customer_id))
                self.conn.commit()
                messagebox.showinfo("Sucesso", f"Status do cliente atualizado para {new_status_text}.")
                self.refresh_customer_list()
                self.refresh_sales_dropdowns() # Atualiza dropdown de vendas
            except sqlite3.Error as e:
                messagebox.showerror("Erro", f"Erro ao atualizar status: {e}")

    def setup_customer_tab(self, frame):
        """Configura a aba de Cadastro de Clientes."""
        
        # Inputs para Cadastrar Cliente
        input_frame = ttk.LabelFrame(frame, text="Cadastrar Novo Cliente", padding="10")
        input_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(input_frame, text="Nome:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.cust_name_entry = ttk.Entry(input_frame, width=30)
        self.cust_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Label(input_frame, text="Telefone:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.cust_phone_entry = ttk.Entry(input_frame, width=30)
        self.cust_phone_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(input_frame, text="Email:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.cust_email_entry = ttk.Entry(input_frame, width=30)
        self.cust_email_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Button(input_frame, text="Cadastrar Cliente", command=self.add_customer).grid(row=3, column=0, columnspan=2, pady=10, sticky='we')
        
        # Visualização de Clientes (Treeview)
        ttk.Label(frame, text="Clientes Cadastrados:", font=("Arial", 12)).pack(pady=(15, 5), anchor='w')

        # Colunas
        columns = ("ID", "Nome", "Telefone", "Email", "Status")
        self.customer_tree = ttk.Treeview(frame, columns=columns, show='headings')
        self.customer_tree.pack(fill='both', expand=True, padx=5, pady=5)

        for col in columns:
            self.customer_tree.heading(col, text=col)
        
        self.customer_tree.column("ID", width=40)
        self.customer_tree.column("Nome", width=180, anchor='w')
        self.customer_tree.column("Telefone", width=100, anchor='center')
        self.customer_tree.column("Email", width=220, anchor='w')
        self.customer_tree.column("Status", width=80, anchor='center')

        # Estilo para inativos
        self.customer_tree.tag_configure('inactive', background='#f0f0f0', foreground='#999999')

        tree_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.customer_tree.yview)
        tree_scroll.pack(side='right', fill='y')
        self.customer_tree.configure(yscrollcommand=tree_scroll.set)

        # Botão para Ativar/Inativar Cliente
        ttk.Button(frame, text="Ativar / Inativar Cliente Selecionado", command=self.toggle_customer_status).pack(pady=10)

    # --- SETUP E LÓGICA DO MÓDULO 5: VENDAS (Mantido) ---
    
    def refresh_sales_history(self):
        """Limpa e recarrega o histórico de vendas."""
        for item in self.sales_tree.get_children(): self.sales_tree.delete(item)

        # Query para incluir o vendedor
        self.cursor.execute("SELECT sale_date, vehicle_info, customer_name, seller_name, final_price FROM sales ORDER BY sale_date DESC")
        sales = self.cursor.fetchall()
        
        for sale in sales:
            date_time, vehicle_info, customer_name, seller_name, final_price = sale
            date_f = date_time.split(' ')[0]
            price_f = f"R$ {final_price:.2f}"
            
            self.sales_tree.insert(
                "", tk.END, values=(date_f, vehicle_info, customer_name, seller_name, price_f)
            )

    def refresh_sales_dropdowns(self):
        """Atualiza os menus de seleção de Veículo, Cliente e Vendedor na aba Vendas."""
        
        # 1. Veículos (em estoque E ATIVOS/DISPONÍVEIS)
        self.cursor.execute("SELECT id, make, model, manufacture_year, model_year, sale_price, stock FROM vehicles WHERE stock > 0 AND is_active = 1 ORDER BY make, model ASC")
        vehicle_rows = self.cursor.fetchall()
        self.available_vehicles = {}
        vehicle_names = []
        
        for vid, make, model, manuf_year, model_year, price, stock in vehicle_rows:
            display_name = f"{make} {model} {manuf_year}/{model_year} (R$ {price:.2f})"
            self.available_vehicles[display_name] = {'id': vid, 'price': price}
            vehicle_names.append(display_name)

        if vehicle_names:
            self.sale_vehicle_var.set(vehicle_names[0])
        else:
            self.sale_vehicle_var.set("Nenhum veículo em estoque")
            
        menu_veh = self.sale_vehicle_menu['menu']
        menu_veh.delete(0, 'end')
        for name in vehicle_names:
            menu_veh.add_command(label=name, command=tk._setit(self.sale_vehicle_var, name))

        # 2. Clientes (APENAS ATIVOS)
        self.cursor.execute("SELECT name FROM customers WHERE is_active = 1 ORDER BY name ASC")
        customer_names = [row[0] for row in self.cursor.fetchall()]
        
        if customer_names:
            self.sale_customer_var.set(customer_names[0])
        else:
            self.sale_customer_var.set("Nenhum Cliente Cadastrado")
            
        menu_cust = self.sale_customer_menu['menu']
        menu_cust.delete(0, 'end')
        for name in customer_names:
            menu_cust.add_command(label=name, command=tk._setit(self.sale_customer_var, name))

        # 3. Vendedores (APENAS ATIVOS)
        self.cursor.execute("SELECT name FROM sellers WHERE is_active = 1 ORDER BY name ASC")
        seller_names = [row[0] for row in self.cursor.fetchall()]

        if seller_names:
            self.sale_seller_var.set(seller_names[0])
        else:
            self.sale_seller_var.set("Nenhum Vendedor Cadastrado")
        
        menu_seller = self.sale_seller_menu['menu']
        menu_seller.delete(0, 'end')
        for name in seller_names:
            menu_seller.add_command(label=name, command=tk._setit(self.sale_seller_var, name))


    def register_sale(self):
        """Registra uma venda."""
        vehicle_display = self.sale_vehicle_var.get()
        customer_name = self.sale_customer_var.get()
        seller_name = self.sale_seller_var.get()
        final_price_str = self.sale_price_entry.get().strip()
        
        if vehicle_display == "Nenhum veículo em estoque" or customer_name == "Nenhum Cliente Cadastrado" or seller_name == "Nenhum Vendedor Cadastrado" or not final_price_str:
            return messagebox.showwarning("Atenção", "Selecione o veículo, o cliente, o vendedor e informe o preço final.")
            
        try:
            final_price = float(final_price_str.replace(',', '.'))
            if final_price <= 0: raise ValueError
        except ValueError:
            return messagebox.showerror("Erro de Entrada", "Preço de venda final inválido.")
            
        # Obtém dados do veículo
        vehicle_data = self.available_vehicles.get(vehicle_display)
        if not vehicle_data:
            return messagebox.showerror("Erro", "Veículo selecionado não é válido.")

        vehicle_id = vehicle_data['id']
        
        try:
            # 1. Atualizar Estoque (deduz 1 unidade)
            self.cursor.execute("UPDATE vehicles SET stock = stock - 1 WHERE id = ? AND stock > 0", (vehicle_id,))
            if self.cursor.rowcount == 0:
                self.conn.rollback()
                return messagebox.showwarning("Estoque", "Estoque insuficiente para este veículo.")
                
            # 2. Registrar Venda
            vehicle_info_for_sale = vehicle_display.split('(')[0].strip()
            date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "INSERT INTO sales (vehicle_id, vehicle_info, customer_name, seller_name, final_price, sale_date) VALUES (?, ?, ?, ?, ?, ?)", 
                (vehicle_id, vehicle_info_for_sale, customer_name, seller_name, final_price, date_time)
            )
            
            # 3. Verificar o estoque após a venda e inativar se chegar a zero (LÓGICA ALTERADA)
            self.cursor.execute("SELECT stock FROM vehicles WHERE id = ?", (vehicle_id,))
            current_stock = self.cursor.fetchone()[0]
            
            if current_stock == 0:
                sale_date_only = datetime.now().strftime("%Y-%m-%d")
                # Inativa e registra a data da venda
                self.cursor.execute("UPDATE vehicles SET is_active = 0, sale_date_only = ? WHERE id = ?", (sale_date_only, vehicle_id))
                messagebox.showinfo("Estoque Zero", f"O veículo {vehicle_info_for_sale} atingiu estoque 0 e foi marcado como VENDIDO e inativado automaticamente.")
            
            self.conn.commit()
            
            messagebox.showinfo("Venda Concluída", f"Venda de {vehicle_info_for_sale} (Vendedor: {seller_name}) registrada por R$ {final_price:.2f}.")
            self.sale_price_entry.delete(0, tk.END)
            self.refresh_sales_dropdowns()
            self.refresh_sales_history()
            self.refresh_inventory_list() # Atualiza estoque na aba de Estoque
            
            # Atualiza gráficos após nova venda
            if self.notebook.tab(self.notebook.select(), "text") == "7. Análise Gráfica":
                self.plot_analytics()
            
        except sqlite3.Error as e:
            self.conn.rollback()
            messagebox.showerror("Erro", f"Erro ao registrar venda: {e}")

    def setup_sales_tab(self, frame):
        """Configura a aba de Gestão de Vendas."""

        # Área de Registro de Vendas
        sale_frame = ttk.LabelFrame(frame, text="Registrar Nova Venda", padding="10")
        sale_frame.pack(fill='x', padx=5, pady=5)
        
        # Variáveis
        self.sale_vehicle_var = tk.StringVar(value="Nenhum veículo em estoque")
        self.sale_customer_var = tk.StringVar(value="Nenhum Cliente Cadastrado")
        self.sale_seller_var = tk.StringVar(value="Nenhum Vendedor Cadastrado")

        # Linha 0: Veículo
        ttk.Label(sale_frame, text="Veículo a ser vendido:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.sale_vehicle_menu = ttk.OptionMenu(sale_frame, self.sale_vehicle_var, self.sale_vehicle_var.get())
        self.sale_vehicle_menu.config(width=40)
        self.sale_vehicle_menu.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        # Linha 1: Cliente
        ttk.Label(sale_frame, text="Cliente Comprador:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.sale_customer_menu = ttk.OptionMenu(sale_frame, self.sale_customer_var, self.sale_customer_var.get())
        self.sale_customer_menu.config(width=40)
        self.sale_customer_menu.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        # Linha 2: Vendedor
        ttk.Label(sale_frame, text="Vendedor:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.sale_seller_menu = ttk.OptionMenu(sale_frame, self.sale_seller_var, self.sale_seller_var.get())
        self.sale_seller_menu.config(width=40)
        self.sale_seller_menu.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        
        # Linha 3: Preço Final
        ttk.Label(sale_frame, text="Preço Final de Venda (R$):").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        self.sale_price_entry = ttk.Entry(sale_frame, width=20)
        self.sale_price_entry.grid(row=3, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Button(sale_frame, text="FINALIZAR VENDA", command=self.register_sale).grid(row=4, column=0, columnspan=2, pady=10, sticky='we')

        # Histórico de Vendas (Treeview)
        ttk.Label(frame, text="Histórico de Transações de Vendas:", font=("Arial", 12)).pack(pady=(15, 5), anchor='w')

        # Colunas
        columns = ("Data", "Veículo", "Cliente", "Vendedor", "Total")
        self.sales_tree = ttk.Treeview(frame, columns=columns, show='headings')
        self.sales_tree.pack(fill='both', expand=True, padx=5, pady=5)

        self.sales_tree.heading("Data", text="Data")
        self.sales_tree.column("Data", width=90, anchor='center')
        self.sales_tree.heading("Veículo", text="Veículo")
        self.sales_tree.column("Veículo", width=200, anchor='w')
        self.sales_tree.heading("Cliente", text="Cliente")
        self.sales_tree.column("Cliente", width=150, anchor='w')
        self.sales_tree.heading("Vendedor", text="Vendedor")
        self.sales_tree.column("Vendedor", width=150, anchor='w')
        self.sales_tree.heading("Total", text="Total Venda")
        self.sales_tree.column("Total", width=100, anchor='e')

        tree_scroll_sales = ttk.Scrollbar(frame, orient="vertical", command=self.sales_tree.yview)
        tree_scroll_sales.pack(side='right', fill='y')
        self.sales_tree.configure(yscrollcommand=tree_scroll_sales.set)

    # --- SETUP E LÓGICA DO MÓDULO 6: RELATÓRIOS (Mantido) ---
    
    def fetch_report_data(self, report_type):
        """Busca os dados do DB baseados no tipo e filtros."""
        include_inactive = self.include_inactive_var.get()
        status_filter_sql = ""

        if report_type == "Estoque":
            threshold = self.get_stock_threshold()
            if threshold is None: return None, None
            
            # Query ATUALIZADA com sale_date_only
            query = f"SELECT id, make, model, manufacture_year, model_year, color, sale_price, stock, is_active, sale_date_only FROM vehicles WHERE stock <= ? ORDER BY stock ASC"
            self.cursor.execute(query, (threshold,))
            data = self.cursor.fetchall()
            
            # Colunas ATUALIZADAS com Status e Data Venda
            columns = ["ID", "Marca", "Modelo", "Ano Fab.", "Ano Mod.", "Cor", "Preço de Venda (R$)", "Estoque", "Status", "Data Venda"]
            
            processed_data = []
            for row in data:
                vid, make, model, manuf_year, model_year, color, price, stock, is_active, sale_date = row
                
                # Aplica o filtro de inativos E a lógica de status
                if not include_inactive and not is_active:
                    continue # Pula inativos se o checkbox não estiver marcado
                
                status_text = "Disponível" if is_active else "Vendido"
                display_sale_date = sale_date if not is_active and sale_date else "" # Mostra data só se Vendido
                
                processed_data.append((
                    vid, make, model, manuf_year, model_year, color, price, stock, status_text, display_sale_date
                ))
                
            return processed_data, columns

        elif report_type == "Vendas":
            start_date = self.start_date_var.get().strip()
            end_date = self.end_date_var.get().strip()
            
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Erro de Filtro", "Formato de data inválido. Use AAAA-MM-DD.")
                return None, None

            # Query para incluir vendedor
            query = """
                SELECT sale_date, vehicle_info, customer_name, seller_name, final_price 
                FROM sales 
                WHERE sale_date BETWEEN ? AND ? || ' 23:59:59' 
                ORDER BY sale_date DESC
            """
            self.cursor.execute(query, (start_date, end_date))
            data = self.cursor.fetchall()
            # Colunas
            columns = ["Data/Hora Venda", "Veículo", "Cliente", "Vendedor", "Total Venda (R$)"]
            return data, columns
            
        return None, None


    def generate_report(self):
        """Gera o relatório em XLSX com base na seleção e filtros."""
        if pd is None:
            messagebox.showerror("Erro de Dependência", "Para gerar relatórios Excel, você precisa instalar as bibliotecas pandas e openpyxl:\nExecute: pip install pandas openpyxl")
            return
            
        report_type = self.report_type.get()
        data, columns = self.fetch_report_data(report_type)
        
        if data is None: return
        if not data:
            return messagebox.showinfo("Relatório Vazio", f"Nenhum dado encontrado para o relatório de {report_type}.")

        default_filename = f"Relatorio_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=default_filename,
            filetypes=[("Excel files", "*.xlsx")],
            title="Salvar Relatório Excel"
        )
        
        if not file_path: return

        try:
            df = pd.DataFrame(data, columns=columns)
            df.to_excel(file_path, index=False, sheet_name=report_type)
            messagebox.showinfo("Sucesso", f"Relatório de {report_type} salvo com sucesso em:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro ao salvar o arquivo: {e}")

    def setup_reports_tab(self, frame):
        """Configura os widgets para a aba de Relatórios."""

        # Seleção do Tipo de Relatório
        type_frame = ttk.LabelFrame(frame, text="Configuração do Relatório", padding="10")
        type_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(type_frame, text="Tipo de Relatório:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        report_options = ["Estoque", "Vendas"]
        
        ttk.OptionMenu(type_frame, self.report_type, self.report_type.get(), *report_options, command=self.toggle_report_filters).grid(row=0, column=1, padx=5, pady=5, sticky='we')
        
        # Frame para os Filtros (será atualizado dinamicamente)
        self.filters_frame = ttk.LabelFrame(frame, text="Filtros Específicos", padding="10")
        self.filters_frame.pack(fill='x', padx=5, pady=5)
        
        self.toggle_report_filters(self.report_type.get())

        # Botão Gerar
        ttk.Button(frame, text="GERAR RELATÓRIO (XLSX)", command=self.generate_report).pack(pady=20, fill='x', padx=5)

    def toggle_report_filters(self, report_type):
        """Alterna os campos de filtro baseados no tipo de relatório selecionado."""
        for widget in self.filters_frame.winfo_children(): widget.destroy()

        if report_type == "Estoque":
            self.filters_frame.config(text="Filtros de Estoque")
            
            ttk.Label(self.filters_frame, text="Estoque abaixo ou igual a (Qtde):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
            self.stock_threshold_entry = ttk.Entry(self.filters_frame, width=10, textvariable=self.stock_threshold_var)
            self.stock_threshold_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')
            ttk.Label(self.filters_frame, text="(Vazio = Todos os veículos)").grid(row=0, column=2, padx=5, pady=5, sticky='w')

            # Checkbox para incluir inativos (NOVO)
            ttk.Checkbutton(
                self.filters_frame, 
                text="Incluir veículos Vendidos/Inativos", 
                variable=self.include_inactive_var
            ).grid(row=1, column=0, columnspan=3, padx=5, pady=10, sticky='w')

        elif report_type == "Vendas":
            self.filters_frame.config(text="Filtros de Vendas por Período (AAAA-MM-DD)")

            ttk.Label(self.filters_frame, text="Data Inicial:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
            self.start_date_entry = ttk.Entry(self.filters_frame, width=15, textvariable=self.start_date_var)
            self.start_date_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')

            ttk.Label(self.filters_frame, text="Data Final:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
            self.end_date_entry = ttk.Entry(self.filters_frame, width=15, textvariable=self.end_date_var)
            self.end_date_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')

    # --- SETUP E LÓGICA DO MÓDULO 7: ANÁLISE GRÁFICA (Mantido) ---
    
    def setup_analytics_tab(self, frame):
        """Configura a aba de Análise Gráfica."""
        # Frame para conter a área do gráfico e o toolbar
        self.plot_container = ttk.Frame(frame)
        self.plot_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        ttk.Label(self.plot_container, text="Clique na aba para carregar gráficos ou instale dependências (pandas, matplotlib)...").pack(pady=20)
        
        # Inicialização do contêiner do Matplotlib (será preenchido em plot_analytics)
        self.matplotlib_canvas = None

    def plot_analytics(self):
        """Gera e exibe os 4 gráficos de análise de dados."""
        if plt is None or pd is None:
            # Garante que a mensagem de erro da dependência seja exibida se estiver faltando
            for widget in self.plot_container.winfo_children(): widget.destroy()
            ttk.Label(self.plot_container, text="ERRO: As bibliotecas pandas e/ou matplotlib não foram carregadas.\nInstale com 'pip install pandas matplotlib'").pack(pady=20)
            return

        # Limpa o contêiner anterior
        for widget in self.plot_container.winfo_children():
            widget.destroy()
        
        # Cria a figura (2 linhas, 2 colunas)
        fig, axes = plt.subplots(2, 2, figsize=(10, 6))
        fig.suptitle('Análise de Dados de Vendas e Estoque de Veículos', fontsize=14)
        
        # --- Consulta de Dados ---
        
        # 1. Dados de Vendas (para Vendas por Mês e Vendas por Vendedor)
        self.cursor.execute("SELECT sale_date, seller_name, final_price FROM sales")
        sales_data = self.cursor.fetchall()
        df_sales = pd.DataFrame(sales_data, columns=['sale_date', 'seller_name', 'final_price'])
        
        # 2. Dados de Estoque (para Estoque por Marca e Preço)
        self.cursor.execute("SELECT make, stock, sale_price FROM vehicles WHERE is_active = 1")
        stock_data = self.cursor.fetchall()
        df_stock = pd.DataFrame(stock_data, columns=['make', 'stock', 'sale_price'])

        
        # --- GRÁFICO 1: Vendas por Mês (Linha) ---
        ax1 = axes[0, 0]
        if not df_sales.empty:
            df_sales['sale_date'] = pd.to_datetime(df_sales['sale_date'])
            df_sales['month_year'] = df_sales['sale_date'].dt.to_period('M')
            sales_by_month = df_sales.groupby('month_year').size()
            
            sales_by_month.plot(kind='line', ax=ax1, marker='o', color='skyblue')
            ax1.set_title('1. Vendas por Mês', fontsize=10)
            ax1.set_xlabel('Mês/Ano', fontsize=8)
            ax1.set_ylabel('Nº de Vendas', fontsize=8)
            ax1.tick_params(axis='x', rotation=45, labelsize=7)
            ax1.grid(axis='y', linestyle='--')
        else:
            ax1.text(0.5, 0.5, 'Sem dados de Vendas', ha='center', va='center', fontsize=10)

        # --- GRÁFICO 2: Estoque Disponível por Marca (Barra) ---
        ax2 = axes[0, 1]
        if not df_stock.empty:
            stock_by_make = df_stock.groupby('make')['stock'].sum().sort_values(ascending=False)
            
            stock_by_make.plot(kind='bar', ax=ax2, color='lightcoral')
            ax2.set_title('2. Estoque Disponível por Marca', fontsize=10)
            ax2.set_xlabel('Marca', fontsize=8)
            ax2.set_ylabel('Qtde. em Estoque', fontsize=8)
            ax2.tick_params(axis='x', rotation=45, labelsize=7)
            ax2.grid(axis='y', linestyle='--')
        else:
            ax2.text(0.5, 0.5, 'Sem veículos Disponíveis', ha='center', va='center', fontsize=10)


        # --- GRÁFICO 3: Top 5 Vendedores (Barra Horizontal) ---
        ax3 = axes[1, 0]
        if not df_sales.empty:
            sales_by_seller = df_sales.groupby('seller_name').size().nlargest(5)
            
            sales_by_seller.plot(kind='barh', ax=ax3, color='lightgreen')
            ax3.set_title('3. Top 5 Vendedores (Nº de Vendas)', fontsize=10)
            ax3.set_xlabel('Nº de Vendas', fontsize=8)
            ax3.set_ylabel('Vendedor', fontsize=8)
            ax3.tick_params(axis='y', labelsize=8)
            ax3.grid(axis='x', linestyle='--')
        else:
            ax3.text(0.5, 0.5, 'Sem dados de Vendedores', ha='center', va='center', fontsize=10)

        # --- GRÁFICO 4: Distribuição de Preço (Histograma) ---
        ax4 = axes[1, 1]
        if not df_stock.empty and not df_stock['sale_price'].empty:
            # Garante que o número de bins é apropriado para a quantidade de dados
            num_bins = min(10, len(df_stock['sale_price'].unique())) if len(df_stock) > 1 else 1
            
            ax4.hist(df_stock['sale_price'], bins=num_bins, color='gold', edgecolor='black')
            ax4.set_title('4. Distribuição de Preços (Estoque Disponível)', fontsize=10)
            ax4.set_xlabel('Preço (R$)', fontsize=8)
            ax4.set_ylabel('Frequência', fontsize=8)
            ax4.ticklabel_format(style='plain', axis='x')
            ax4.tick_params(axis='x', rotation=45, labelsize=7)
        else:
            ax4.text(0.5, 0.5, 'Sem dados de Preço para Estoque', ha='center', va='center', fontsize=10)

        # Ajusta o layout para evitar sobreposição
        fig.tight_layout(rect=[0, 0.03, 1, 0.95])

        # --- Embedding Matplotlib na Aba Tkinter ---
        
        # Cria o Canvas do Matplotlib
        self.matplotlib_canvas = FigureCanvasTkAgg(fig, master=self.plot_container)
        canvas_widget = self.matplotlib_canvas.get_tk_widget()
        canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Adiciona a Barra de Ferramentas (Zoom, Pan, Salvar)
        toolbar = NavigationToolbar2Tk(self.matplotlib_canvas, self.plot_container)
        toolbar.update()
        self.matplotlib_canvas.draw()
        
    # --- NOVO MÓDULO 8: GESTÃO DE USUÁRIOS (ADMIN) ---

    def refresh_user_list(self):
        """Limpa e recarrega a Treeview de Usuários."""
        for item in self.user_tree.get_children(): self.user_tree.delete(item)

        self.cursor.execute("SELECT id, username, name, role FROM users ORDER BY role DESC, username ASC")
        users = self.cursor.fetchall()
        for user in users:
            uid, username, name, role = user
            tag = 'admin' if role == 'Admin' else 'user'
            self.user_tree.insert("", tk.END, values=(uid, username, name, role), tags=(tag,))

    def add_user(self):
        """Adiciona um novo usuário (padrão 'Usuário')."""
        username = self.user_username_entry.get().strip()
        name = self.user_name_entry.get().strip().title()
        password = self.user_password_entry.get().strip()

        if not username or not password or not name:
            return messagebox.showwarning("Atenção", "Todos os campos de cadastro são obrigatórios.")
        
        hashed_password = hash_password(password)
        
        try:
            # Novo usuário é sempre criado com perfil "Usuário"
            self.cursor.execute(
                "INSERT INTO users (username, hashed_password, role, name) VALUES (?, ?, ?, ?)", 
                (username, hashed_password, 'Usuário', name)
            )
            self.conn.commit()
            messagebox.showinfo("Sucesso", f"Usuário '{username}' ({name}) cadastrado com perfil 'Usuário'.")
            
            # Limpa campos
            self.user_username_entry.delete(0, tk.END)
            self.user_name_entry.delete(0, tk.END)
            self.user_password_entry.delete(0, tk.END)
            self.refresh_user_list()
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", "Nome de usuário já existe. Escolha outro.")
        except sqlite3.Error as e:
            messagebox.showerror("Erro", f"Erro: {e}")

    def setup_admin_tab(self, frame):
        """Configura a aba de Gestão de Usuários (Apenas Admin)."""
        
        # Inputs para Cadastrar Novo Usuário
        input_frame = ttk.LabelFrame(frame, text="Cadastrar Novo Usuário (Perfil Padrão: Usuário)", padding="10")
        input_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(input_frame, text="Nome Completo:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.user_name_entry = ttk.Entry(input_frame, width=30)
        self.user_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Label(input_frame, text="Nome de Usuário:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.user_username_entry = ttk.Entry(input_frame, width=30)
        self.user_username_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(input_frame, text="Senha:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.user_password_entry = ttk.Entry(input_frame, show="*", width=30)
        self.user_password_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Button(input_frame, text="Cadastrar Usuário", command=self.add_user).grid(row=3, column=0, columnspan=2, pady=10, sticky='we')
        
        # Visualização de Usuários (Treeview)
        ttk.Label(frame, text="Usuários Cadastrados:", font=("Arial", 12)).pack(pady=(15, 5), anchor='w')

        columns = ("ID", "Username", "Nome", "Perfil")
        self.user_tree = ttk.Treeview(frame, columns=columns, show='headings')
        self.user_tree.pack(fill='both', expand=True, padx=5, pady=5)

        for col in columns:
            self.user_tree.heading(col, text=col)
        
        self.user_tree.column("ID", width=40)
        self.user_tree.column("Username", width=150, anchor='w')
        self.user_tree.column("Nome", width=250, anchor='w')
        self.user_tree.column("Perfil", width=100, anchor='center')

        # Estilo para perfis
        self.user_tree.tag_configure('admin', foreground='red', font=('Arial', 9, 'bold'))
        self.user_tree.tag_configure('user', foreground='blue')

        tree_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.user_tree.yview)
        tree_scroll.pack(side='right', fill='y')
        self.user_tree.configure(yscrollcommand=tree_scroll.set)

# --- EXECUÇÃO DO APLICATIVO ---

if __name__ == "__main__":
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()
