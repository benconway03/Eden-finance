import matplotlib
matplotlib.use("Agg")               # headless backend for servers
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
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


def inv_calc_futr(start_amount, 
                  time_period_years, 
                  time_period_months, 
                  annual_return_rate, 
                  contributions, 
                  contribution_timing):
    
    # --- 1. VALIDATION & CALCULATION (Unchanged) ---
    if contribution_timing not in ('Yearly', 'Monthly'):
        raise ValueError("Wrong Contribution Timing")
    
    wealth = [start_amount]
    pot_sav = [start_amount]
    total_time_months = time_period_years * 12 + time_period_months
    
    # Calculate monthly return rate
    return_rate_monthly = (1 + annual_return_rate / 100) ** (1 / 12)
    
    # generate contribution list
    if contribution_timing == 'Monthly':
        cont_lst = [contributions] * (total_time_months + 1)
    elif contribution_timing == 'Yearly':
        cont_lst = [contributions if i % 12 == 0 and i != 0 else 0 for i in range(total_time_months + 1)]
        
    # compound loop
    for i in range(1, total_time_months + 1):
        wealth.append(wealth[i-1] * return_rate_monthly + cont_lst[i])
        pot_sav.append(cont_lst[i] + pot_sav[i-1])

    # --- 2. STYLING & PLOTTING (Updated) ---
    
    # Create figure with a slightly wider aspect ratio
    fig, ax = plt.subplots(figsize=(10, 6))

    # COLORS FROM YOUR CSS
    COLOR_NAVY = '#0a1d36'
    COLOR_MID  = '#2366af'
    COLOR_SKY  = '#d3dff1'
    COLOR_GREY = '#b5c5dc'

    # Plot 1: Total Portfolio Value (The "Hero" line)
    # We use a solid navy line and fill underneath it with the "sky" color
    ax.plot(wealth, color=COLOR_NAVY, linewidth=2.5, label='Projected Value')
    ax.fill_between(range(len(wealth)), wealth, color=COLOR_SKY, alpha=0.4)

    # Plot 2: Contributions (The "Baseline")
    # We use a dashed line to differentiate "money in" vs "money growth"
    ax.plot(pot_sav, color=COLOR_MID, linestyle='--', linewidth=2, label='Total Contributed')

    # --- 3. PROFESSIONAL FORMATTING ---

    # Remove top and right borders (spines) for a cleaner look
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Color the remaining spines to match your theme (optional, or keep default black)
    ax.spines['left'].set_color(COLOR_NAVY)
    ax.spines['bottom'].set_color(COLOR_NAVY)

    # Grid: subtle, dotted, and sent to the back
    ax.grid(True, which='major', axis='y', linestyle=':', color=COLOR_GREY, alpha=0.7)
    ax.set_axisbelow(True)

    # Titles and Labels (Using a sans-serif font to match Helvetica/Arial)
    ax.set_title(f"Projected Wealth over {time_period_years} Years, {time_period_months} Months", 
                 fontsize=14, fontweight='bold', color=COLOR_NAVY, pad=20)
    
    ax.set_xlabel("Months Elapsed", fontsize=11, color=COLOR_NAVY, labelpad=10)
    # Removed Y-label text "Value" because the currency sign makes it obvious
    
    # Legend: simple frame, keeping it clean
    ax.legend(loc='upper left', frameon=True, fontsize=10)

    # --- 4. CURRENCY FORMATTING ---
    # This formats the Y-axis to look like currency (e.g. £10,000)
    fmt = '£{x:,.0f}'
    tick = mtick.StrMethodFormatter(fmt)
    ax.yaxis.set_major_formatter(tick)

    # Adjust layout to prevent clipping
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

@app.route('/resource_lib')
def resource_lib():
    return render_template('resource_lib.html')

@app.route('/market_pulse')
def market_pulse():
    return render_template('market_pulse.html')

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

