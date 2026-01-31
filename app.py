import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd

# ---------------- DB CONNECTION ----------------
conn = sqlite3.connect("database.db", check_same_thread=False)
c = conn.cursor()

# ---------------- TABLES ----------------
# Admin table
c.execute("""CREATE TABLE IF NOT EXISTS admin (
    username TEXT PRIMARY KEY,
    password TEXT
)""")

# Products table
c.execute("""CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    category TEXT,
    buy_price REAL,
    sell_price REAL,
    quantity INTEGER
)""")
conn.commit()

# Sold products table
c.execute("""CREATE TABLE IF NOT EXISTS sold_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    category TEXT,
    buy_price REAL,
    sell_price REAL,
    quantity INTEGER,
    date_sold TEXT
)""")
conn.commit()

# ---------------- SAFE MIGRATION ----------------
# Add date_added column if missing in products
c.execute("PRAGMA table_info(products)")
cols = [col[1] for col in c.fetchall()]
if "date_added" not in cols:
    c.execute("ALTER TABLE products ADD COLUMN date_added TEXT")
    conn.commit()

# Add buy_price column if missing in sold_products
c.execute("PRAGMA table_info(sold_products)")
cols_sold = [col[1] for col in c.fetchall()]
if "buy_price" not in cols_sold:
    c.execute("ALTER TABLE sold_products ADD COLUMN buy_price REAL")
    conn.commit()

# ---------------- PASSWORD HASH ----------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ---------------- DEFAULT ADMIN ----------------
c.execute("SELECT * FROM admin")
if not c.fetchone():
    c.execute(
        "INSERT INTO admin VALUES (?, ?)",
        ("admin", hash_password("admin123"))
    )
    conn.commit()

# ---------------- LOGIN ----------------
def login():
    st.title("Connexion Administrateur")

    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        c.execute(
            "SELECT * FROM admin WHERE username=? AND password=?",
            (username, hash_password(password))
        )
        if c.fetchone():
            st.session_state.logged_in = True
            st.success("Connexion réussie")
            st.rerun()
        else:
            st.error("Identifiants incorrects")

# ---------------- DASHBOARD ----------------
def dashboard():
    st.title("📊 Dashboard")

    # Total stock
    c.execute("SELECT SUM(quantity) FROM products")
    total_stock = c.fetchone()[0] or 0

    # Total sold
    c.execute("SELECT SUM(quantity) FROM sold_products")
    total_sold = c.fetchone()[0] or 0

    # Total revenue
    c.execute("SELECT SUM(sell_price * quantity) FROM sold_products")
    total_revenue = c.fetchone()[0] or 0.0

    # Total profit
    c.execute("SELECT SUM((sell_price - buy_price) * quantity) FROM sold_products")
    total_profit = c.fetchone()[0] or 0.0

    # Number of categories
    c.execute("SELECT COUNT(DISTINCT category) FROM products")
    num_categories = c.fetchone()[0] or 0

    # KPI metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Produits en Stock", total_stock)
    col2.metric("Produits Vendus", total_sold)
    col3.metric("Revenu Total", f"{total_revenue}")
    col4.metric("Profit Total", f"{total_profit}")
    col5.metric("Catégories", num_categories)

    st.markdown("---")

    # ---------------- Stock Insights ----------------
    st.subheader("📦 Produits Low Stock")
    c.execute("SELECT name, category, quantity FROM products WHERE quantity <=5 ORDER BY quantity ASC")
    low_stock = c.fetchall()
    if low_stock:
        st.table([{"Nom": r[0], "Catégorie": r[1], "Quantité": r[2]} for r in low_stock])
    else:
        st.info("Aucun produit avec stock faible.")

    st.subheader("📦 Top 5 Produits par Stock")
    c.execute("SELECT name, category, quantity FROM products ORDER BY quantity DESC LIMIT 5")
    top_stock = c.fetchall()
    if top_stock:
        st.table([{"Nom": r[0], "Catégorie": r[1], "Quantité": r[2]} for r in top_stock])

    st.subheader("📈 Revenus par Catégorie")
    c.execute("SELECT category, SUM(sell_price * quantity), SUM((sell_price - buy_price) * quantity) FROM sold_products GROUP BY category")
    cat_data = c.fetchall()
    if cat_data:
        df_cat = pd.DataFrame(cat_data, columns=["Catégorie", "Revenu", "Profit"])
        st.bar_chart(df_cat.set_index("Catégorie")[["Revenu", "Profit"]])

# ---------------- MAIN APP ----------------
def app():
    st.title("Gestion de Commerce")

    # Logout button
    if st.sidebar.button("Déconnexion"):
        st.session_state.logged_in = False
        st.rerun()

    menu = st.sidebar.selectbox("Menu", ["Dashboard", "Produits", "Stock", "Vente", "Ventes"])

    if menu == "Dashboard":
        dashboard()

    # ---------------- ADD PRODUCT ----------------
    elif menu == "Produits":
        st.subheader("Ajouter un produit")

        name = st.text_input("Nom")
        category = st.selectbox(
            "Catégorie",
            ["Habits", "Perruques", "Greffes", "Lace Frontal", "Closures", "Chains", "Sous-vêtements"]
        )
        buy_price = st.number_input("Prix d'achat", min_value=0.0)
        sell_price = st.number_input("Prix de vente", min_value=0.0)
        quantity = st.number_input("Quantité", min_value=0, step=1)

        if st.button("Ajouter"):
            if not name:
                st.warning("Veuillez entrer le nom du produit.")
            else:
                date_now = datetime.now().strftime("%Y-%m-%d %H:%M")
                c.execute(
                    "INSERT INTO products (name, category, buy_price, sell_price, quantity, date_added) "
                    "VALUES (?,?,?,?,?,?)",
                    (name, category, buy_price, sell_price, quantity, date_now)
                )
                conn.commit()
                st.success(f"Produit '{name}' ajouté avec succès ✅")

    # ---------------- STOCK ----------------
    elif menu == "Stock":
        st.subheader("Liste des produits")

        # Get categories for filter
        c.execute("SELECT DISTINCT category FROM products")
        categories = [r[0] for r in c.fetchall()]
        selected = st.selectbox("Filtrer par catégorie", ["Toutes"] + categories)

        if selected == "Toutes":
            c.execute("""
                SELECT name, category, buy_price, sell_price, quantity, date_added
                FROM products
            """)
        else:
            c.execute("""
                SELECT name, category, buy_price, sell_price, quantity, date_added
                FROM products
                WHERE category = ?
            """, (selected,))

        rows = c.fetchall()

        if rows:
            st.table(
                [{"Nom": r[0],
                  "Catégorie": r[1],
                  "Prix Achat": r[2],
                  "Prix Vente": r[3],
                  "Quantité": r[4],
                  "Ajouté le": r[5]} for r in rows]
            )
        else:
            st.info("Aucun produit trouvé pour cette catégorie.")

    # ---------------- SELL PRODUCT ----------------
    elif menu == "Vente":
        st.subheader("Vendre un produit")

        # Products with stock > 0
        c.execute("SELECT id, name, category, buy_price, sell_price, quantity FROM products WHERE quantity > 0")
        products = c.fetchall()

        if not products:
            st.warning("Aucun produit disponible à la vente.")
        else:
            product_map = {f"{p[1]} ({p[2]}) - Stock: {p[5]}": p for p in products}
            choice = st.selectbox("Produit", list(product_map.keys()))
            prod = product_map[choice]

            sell_qty = st.number_input(
                "Quantité à vendre",
                min_value=1,
                max_value=prod[5],
                step=1,
                value=1
            )

            if st.button("Valider la vente"):
                new_qty = prod[5] - sell_qty
                date_now = datetime.now().strftime("%Y-%m-%d %H:%M")

                # Update stock
                c.execute(
                    "UPDATE products SET quantity=? WHERE id=?",
                    (new_qty, prod[0])
                )

                # Insert into sold_products with buy_price
                c.execute("""
                    INSERT INTO sold_products (name, category, buy_price, sell_price, quantity, date_sold)
                    VALUES (?,?,?,?,?,?)
                """, (prod[1], prod[2], prod[3], prod[4], sell_qty, date_now))

                conn.commit()

                # Show success message
                st.success(f"Vente de {sell_qty} '{prod[1]}' enregistrée et stock mis à jour ✅")

    # ---------------- SOLD PRODUCTS HISTORY ----------------
    elif menu == "Ventes":
        st.subheader("Produits vendus")

        c.execute("""
            SELECT name, category, buy_price, sell_price, quantity, date_sold
            FROM sold_products
            ORDER BY date_sold DESC
        """)
        rows = c.fetchall()

        if rows:
            st.table([
                {
                    "Nom": r[0],
                    "Catégorie": r[1],
                    "Prix Achat": r[2],
                    "Prix Vente": r[3],
                    "Quantité": r[4],
                    "Bénéfice": (r[3] - r[2]) * r[4],
                    "Vendu le": r[5]
                } for r in rows
            ])
        else:
            st.info("Aucune vente enregistrée pour le moment.")

# ---------------- SESSION STATE ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------- ROUTER ----------------
if st.session_state.logged_in:
    app()
else:
    login()