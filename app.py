from flask import Flask, render_template_string
from master_analyzer import MasterAnalyzer

analyzer = MasterAnalyzer()

app = Flask(__name__)

@app.route('/')
def show_dfs():
    
    head = """
        <head>
            <title>DataFrame Viewer</title>
            <style>
                table { border-collapse: collapse; }
                th, td { padding: 8px 12px; border: 1px solid #ccc; }
                th { background-color: #f4f4f4; }
            </style>
        </head>
    """
    body = """
        <body>
            <h2>DataFrames</h2>
            {% for name, table_html in tables.items() %}
                <h3>{{ name }}</h3>
                {{ table_html | safe }}
            {% endfor %}
        </body>
    """
    return render_template_string("""
    <html>
        <head>
            <title>DataFrame Viewer</title>
            <style>
                table { border-collapse: collapse; }
                th, td { padding: 8px 12px; border: 1px solid #ccc; }
                th { background-color: #f4f4f4; }
            </style>
        </head>
        <body>
            <h2>DataFrames</h2>
            {% for name, table_html in tables.items() %}
                <h3>{{ name }}</h3>
                {{ table_html | safe }}
            {% endfor %}
        </body>                    
    </html>                              
    """, tables={name: df.to_html(classes='dataframe', header=True, index=False) 
                 for name, df in analyzer.get_dfs_from_presenter().items()})




def main():
    app.run(debug=True)
    
if __name__ == "__main__":
    main()