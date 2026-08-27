# 🧠 Intelligent Data Analysis Assistant (IDAA)

A full-stack **Data Science mini-project** — a Flask web application that lets users
upload a dataset (CSV/Excel) and instantly get automated exploratory data analysis
(EDA), interactive visualizations, and a no-code filter/query builder, all wrapped
in a polished, modern dark/light UI.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 **Authentication** | Secure user registration & login (hashed passwords) with Flask-Login |
| 🗄️ **Database** | SQLite database (via SQLAlchemy) stores users, datasets & query history |
| 📤 **Upload Engine** | Upload `.csv`, `.xlsx`, `.xls` files up to 25 MB |
| 🧹 **Data Cleaning** | Normalizes headers, missing values, text, numeric/date fields, empty rows, and duplicates before analysis; download the cleaned CSV from the analysis page |
| 📊 **Automated EDA** | Row/column counts, missing values, duplicates, dtype detection, column profiling |
| 🧮 **No-Code Query Builder** | Filter rows with column/operator/value rules (AND logic) + paginated results |
| 📈 **Group & Aggregate** | Group by any column and aggregate (sum/mean/count/max/min/median) with auto-chart |
| 🎨 **Custom Chart Builder** | Build bar, line, scatter, pie, box and histogram charts on any columns |
| 🌡️ **Correlation Heatmap** | Automatic correlation matrix for numeric columns |
| 📄 **PDF Report Export** | One-click polished PDF report (overview, data quality and column profile) |
| 🌓 **Dark / Light Theme** | Toggle-able glassmorphism UI theme, persisted in local storage |
| 📱 **Responsive UI** | Built with Bootstrap 5 + custom design system, works on mobile |

---

## 🏗️ Tech Stack

- **Backend:** Python 3, Flask, Flask-SQLAlchemy, Flask-Login
- **Database:** SQLite (file-based, zero-config)
- **Data Processing:** Pandas, NumPy
- **Visualization:** Plotly (interactive charts, server-rendered JSON → client-rendered)
- **PDF Generation:** ReportLab
- **Frontend:** HTML5, Bootstrap 5, Bootstrap Icons, vanilla JavaScript (no build step needed)

---

## 📁 Project Structure

```
IDAA_Project/
│
├── app.py                     # Main Flask application (routes, API endpoints)
├── config.py                  # App configuration (DB URI and upload settings)
├── models.py                  # SQLAlchemy models: User, Dataset, QueryHistory
├── requirements.txt           # Python dependencies
├── run.bat                    # One-click launcher for Windows
├── run.sh                     # One-click launcher for macOS/Linux
├── README.md                  # This file
│
├── utils/
│   ├── eda.py                 # Auto-EDA engine (overview, profiling, charts)
│   ├── query_engine.py        # Safe (no-eval) filter & group-by engine
│   └── report_generator.py    # PDF report builder (ReportLab)
│
├── templates/                 # Jinja2 HTML templates
│   ├── base.html               # Shared layout (navbar, theme toggle, footer)
│   ├── index.html              # Landing page
│   ├── login.html / register.html
│   ├── dashboard.html          # User's dataset list + stats
│   ├── upload.html             # File upload page
│   ├── analysis.html           # Auto-EDA results + charts
│   ├── query.html              # Filter & group-by query builder
│   ├── visualize.html          # Custom chart builder
│   └── errors/404.html
│
├── static/
│   ├── css/style.css           # Full design system (dark/light glassmorphism theme)
│   └── js/main.js              # Theme toggle + shared JS helpers
│
├── sample_data/
│   └── sample_indian_retail_sales.csv   # Ready-to-use sample dataset (400 rows)
│
├── database/                  # SQLite .db file is auto-created here on first run
└── uploads/                   # Uploaded datasets are stored here (per user folder)
```

---

## 🚀 Getting Started

### Option A — One-click launcher (easiest)

**Windows:** double-click **`run.bat`**
**macOS / Linux:** open a terminal in the project folder and run:
```bash
./run.sh
```

These scripts automatically create a virtual environment, install all dependencies,
and start the server at **http://127.0.0.1:5000**.

### Deploy to Render

1. Push this project to a GitHub repository.
2. In Render, create a new **Blueprint** and select the repository.
3. Render will use `render.yaml` to install dependencies and start the app.
4. Set a strong random `SECRET_KEY` environment variable in Render.

The free Render filesystem is ephemeral. SQLite data and uploaded files can be lost
when the service is redeployed, so use a persistent disk and hosted database for
production use.

### Option B — Manual setup (recommended inside VS Code)

1. **Open the folder in VS Code**
   ```
   File → Open Folder → select IDAA_Project
   ```

2. **Create & activate a virtual environment**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**
   ```bash
   python app.py
   ```
   Or press **F5** in VS Code (a ready-made `.vscode/launch.json` is included —
   just make sure the Python extension is installed and the interpreter is set
   to `venv`).

5. **Open your browser** at [http://127.0.0.1:5000](http://127.0.0.1:5000)

> The SQLite database (`database/idaa.db`) and required folders are created
> automatically the first time you run the app — no manual DB setup needed.

---

## 🧪 Try It Out

1. Register a new account on the landing page.
2. Go to **Upload** and select the included sample file:
   `sample_data/sample_indian_retail_sales.csv`
   (400 rows of realistic Indian e-commerce sales data — cities, categories,
   payment modes, prices, ratings, etc.)
3. Land automatically on the **Analysis** page to see:
   - Row/column stats, missing values, duplicates
   - Column profile table
   - Correlation heatmap, distribution charts, category breakdowns
4. Click **Query Builder** to filter rows (e.g. `City equals Mumbai` AND
   `TotalRevenue greater_than 5000`) or group by `ProductCategory` and sum
   `SalesAmount`.
5. Click **Chart Builder** to build any custom chart on any columns.
6. Click **Export PDF** to download a shareable summary report.

---

## 🛠️ Customization Ideas (for extending the project)

- Add more chart types (heatmap, treemap, sunburst) using Plotly Express
- Add scheduled/periodic dataset refresh via a background job
- Add role-based access (admin vs analyst)
- Deploy to Render / Railway / PythonAnywhere for a public demo

---

## 📌 Notes

- This project uses CDN links for Bootstrap, Bootstrap Icons and Plotly.js,
  so an internet connection is required in the browser the first time each
  page loads (they are cached afterward).
- Maximum upload size is 25 MB by default (configurable in `config.py`).
- All passwords are hashed with Werkzeug's `generate_password_hash` — never
  stored in plain text.

---

## 👤 Author

Built as a Data Science mini-project — **Intelligent Data Analysis Assistant**.

---

## 📜 License

Free to use and modify for academic and learning purposes.
