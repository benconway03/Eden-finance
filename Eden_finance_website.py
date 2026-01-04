import matplotlib
matplotlib.use("Agg")               # headless backend for servers
import matplotlib.pyplot as plt
import yfinance as yf
import pandas as pd
from flask import Flask, render_template, request
import io, base64, datetime as dt

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


def inv_calc_futr(  start_amount, 
                    time_period_years, 
                    time_period_months, 
                    annual_return_rate, 
                    contributions, 
                    contribution_timing):
    if contribution_timing not in ('Yearly', 'Monthly'):
        raise ValueError("Wrong Contribution Timing")
    else:
        wealth = [start_amount]
        total_time_months = time_period_years*12 + time_period_months
        return_rate_monthly = (1+annual_return_rate/100)**(1/12)
        if contribution_timing == 'Monthly':
            cont_lst = [contributions]*(total_time_months+1)
        elif contribution_timing == 'Yearly':
            cont_lst = [contributions if i % 12 == 0 and i != 0 else 0 for i in range(total_time_months+1)]
        total_time_months = time_period_years*12 + time_period_months
        for i in range (1, total_time_months+1):
            wealth.append(wealth[i-1]*return_rate_monthly + cont_lst[i])
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(wealth, label='Portfolio Value')
    ax.set_title(f"Projected Wealth over {total_time_months} Months")
    ax.set_xlabel("Months")
    ax.set_ylabel("Value (£)")
    ax.grid(True)
    ax.legend()
    fig.tight_layout()
    return fig



# app.py

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
    plot_url = None
    error = None
    
    # Default values to show in the form initially
    defaults = {
        'start_amount': 1000,
        'years': 10,
        'months': 0,
        'rate': 7.0,
        'contribution': 100,
        'timing': 'Monthly'
    }

    if request.method == 'POST':
        try:
            # 1. Get data from form
            start_amount = float(request.form.get('start_amount'))
            years = int(request.form.get('years'))
            months = int(request.form.get('months'))
            rate = float(request.form.get('rate'))
            contribution = float(request.form.get('contribution'))
            timing = request.form.get('timing')

            # Update defaults so the form keeps the values user typed
            defaults = {
                'start_amount': start_amount, 'years': years, 'months': months,
                'rate': rate, 'contribution': contribution, 'timing': timing
            }

            # 2. Run Calculation
            fig = inv_calc_futr(start_amount, years, months, rate, contribution, timing)

            # 3. Convert Plot to Image (Base64)
            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            buf.seek(0)
            plot_url = base64.b64encode(buf.read()).decode("ascii")
            plt.close(fig) # Clean up memory

        except Exception as e:
            error = f"Error: {str(e)}"

    return render_template('investment_calculator.html', 
                           plot_url=plot_url, 
                           error=error, 
                           defaults=defaults)

if __name__ == "__main__":
    app.run(debug=True)

