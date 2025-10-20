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


@app.route("/", methods=["GET", "POST"])
def index():
    plot_url = error = None

    # ----------- defaults the template can reuse ------------
    start_default = "2010-01-01"
    end_default   = dt.date.today().isoformat()

    if request.method == "POST":
        try:
            # ① NEW — pick the dates from <input type=date>
            start_date = request.form.get("start_date", start_default)
            end_date   = request.form.get("end_date",   end_default)

            if start_date >= end_date:
                raise ValueError("End date must be after start date")

            tickers = request.form.getlist("ticker[]")
            amounts = [float(x) for x in request.form.getlist("amount[]")]
            stocks  = list(zip(tickers, amounts))

            # reroute inv_calc to *return* the figure
            fig = inv_calc(start_date, end_date, stocks, return_fig=True)

            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            buf.seek(0)
            plot_url = base64.b64encode(buf.read()).decode("ascii")

        except Exception as e:
            error = str(e)

    return render_template(
        "index.html",
        plot_url=plot_url,
        error=error,
        start_default=start_default,
        end_default=end_default
    )

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == "__main__":
    app.run(debug=True)

