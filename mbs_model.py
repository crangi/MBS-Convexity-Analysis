import numpy as np
import pandas as pd
from decimal import Decimal, getcontext
getcontext().prec = 6

class PrepaymentModel:
    def __init__(self, mbs_amount=100000000, wac=0.05, wam=360, market_rates=0.05,
                 min_cpr=0.0, base_cpr = 0.05, max_cpr=0.3, incentive_cutoff=0.02):
        """
        Info: Initialize the prepayment model with MBS parameters
        Params:
        mbs_amount (float)              : The total amount of the mortgage-backed security
        wac (float)                     : Weighted average coupon of the MBS
        wam (int)                       : Weighted average maturity of the MBS in months
        market_rates (float)/(list)     : Market interest rates 
        """
        self.mbs_amount = mbs_amount
        self.wac = wac
        self.monthly_wac = wac/12
        self.wam = wam
        self.market_rates = market_rates

        # S-Curve parameters
        self.min_cpr = min_cpr
        self.base_cpr = base_cpr
        self.max_cpr = max_cpr
        self.incentive_cutoff = incentive_cutoff

        self.monthly_payment = self.mbs_amount * (self.monthly_wac / (1 - (1/(1 + self.monthly_wac)) **self.wam))

    def get_market_rate(self, month):
        """
        Info: Returns the market rate for a specific month (1-indexed)
        Params:
        month (int) : The month number in a simulation period
        """
        if isinstance(self.market_rates, (list, np.ndarray)):
            # If a list is provided, return the rate of the given month
            return self.market_rates[min(month - 1, len(self.market_rates) - 1)]
        # If interest rate is constant, return a single float
        return self.market_rates
    
    def calculate_monthly_cpr(self, market_rate):
        """
        Info: Calculate the Conditional Prepayment Rate (CPR) using simplified S-Curve model
        Out: Returns a list of CPR values for each month
        """
        incentive = Decimal(self.wac) - Decimal(market_rate)

        if incentive < 0:
            return self.min_cpr
        elif incentive == 0:
            return self.base_cpr
        elif incentive >= self.incentive_cutoff:
            return self.max_cpr
        else:
            slope = (self.max_cpr - self.base_cpr)/self.incentive_cutoff  # linear slope between 5% and 30% for incentives between 0% and 2%
            return self.base_cpr + slope * float(incentive)
    
    def simulate_cashflow(self, num_months=None):
        """
        Info: Simulate the cash flows of the MBS over given months
        Out: Returns a DataFrame with monthly cash flows
        """
        num_months = num_months or self.wam
        monthly_rate = self.monthly_wac
        monthly_payment = self.monthly_payment
        balance = self.mbs_amount
        cashflows = []

        for month in range(1, num_months + 1):

            if balance <=0: break;

            market_rate = self.get_market_rate(month)
            cpr = self.calculate_monthly_cpr(market_rate)
            smm = 1 - (1 - cpr) ** (1 / 12)

            interest = balance * monthly_rate
            scheduled_principal = monthly_payment - interest 
            prepayment = (balance - scheduled_principal) * smm
            total_principal = scheduled_principal + prepayment
            monthly_cashflow = total_principal + interest
            balance -= total_principal
            cashflows.append({
                'Month': month,
                'Interest Rate': market_rate,
                'Prepayment Rate': cpr,
                'Scheduled Principal': scheduled_principal,
                'Prepayment': prepayment,
                'Total Principal': total_principal,
                'Interest': interest,
                'Total Cashflow': monthly_cashflow,
                'Remaining Balance': balance
            })
        
        return pd.DataFrame(cashflows)