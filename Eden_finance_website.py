import matplotlib
matplotlib.use("Agg")               # headless backend for servers
import matplotlib.pyplot as plt
import yfinance as yf
import pandas as pd

def inv_calc(start_date, end_date, stocks, *, return_fig=False):
    if not stocks or not all(isinstance(t, tuple) and len(t) == 2 for t in stocks):
        raise ValueError("stocks must be an iterable of (ticker, amount) tuples")

    tickers, amounts = zip(*stocks)
    amounts = pd.Series(amounts, index=tickers, dtype=float)

    raw   = yf.download(list(tickers),
                        start=start_date,
                        end=end_date,
                        auto_adjust=True,
                        progress=False)
    close = raw["Close"].to_frame() if isinstance(raw["Close"], pd.Series) else raw["Close"]
    close = close.loc[:, tickers]
    initial = close.iloc[0]
    multipliers = amounts / initial

    values = close.multiply(multipliers, axis=1)
    values.columns = [f"{c}_value" for c in values.columns]

    ax = values.plot(figsize=(10, 5), title="Value of Investments (£)", grid=True)
    ax.set_xlabel("Date"); ax.set_ylabel("£")
    fig = ax.get_figure()
    fig.tight_layout()

    if return_fig:
        return fig                     # <-- new behaviour
    return values                      # keep old behaviour available



# app.py
from flask import Flask, render_template, request
import io, base64, datetime as dt

app = Flask(__name__)


@app.route("/")
def index():
    # Simple text for the homepage
    return render_template("index.html")

@app.route("/stocks", methods=["GET", "POST"])
def stocks():
    plot_url = error = None
    start_default = "2010-01-01"
    end_default   = dt.date.today().isoformat()

    if request.method == "POST":
        try:
            # Get dates from the form
            start_date = request.form.get("start_date", start_default)
            end_date   = request.form.get("end_date", end_default)

            if start_date >= end_date:
                raise ValueError("End date must be after start date")

            # Get tickers and amounts
            tickers = request.form.getlist("ticker[]")
            amounts = request.form.getlist("amount[]")

            # Validate input
            if not tickers or not amounts:
                raise ValueError("Please enter at least one ticker and amount")
            
            try:
                amounts = [float(x) for x in amounts]
            except ValueError:
                raise ValueError("Amounts must be numbers")

            stocks_list = list(zip(tickers, amounts))

            # Call the investment calculator
            fig = inv_calc(start_date, end_date, stocks_list, return_fig=True)

            # Check if fig returned anything
            if fig is None:
                raise ValueError("No data available for the provided tickers/dates")

            # Convert figure to PNG for rendering
            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            buf.seek(0)
            plot_url = base64.b64encode(buf.read()).decode("ascii")

        except Exception as e:
            error = str(e)

    return render_template(
        "stocks.html",
        plot_url=plot_url,
        error=error,
        start_default=start_default,
        end_default=end_default
    )

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/investment-calculator', methods=['GET', 'POST'])
def investment_calculator():
    # You can add calculation logic here later. 
    # For now, it simply renders the new page.
    return render_template('investment_calculator.html')

if __name__ == "__main__":
    app.run(debug=True)

