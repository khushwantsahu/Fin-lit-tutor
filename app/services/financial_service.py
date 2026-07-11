
"""
Financial Calculator Service
EMI, Budget, Health Score, Savings Plans
"""

import math
from typing import Dict, List, Optional
from datetime import date, timedelta
import datetime


class FinancialCalculator:

    # ── EMI Calculator ─────────────────────────────────────────

    @staticmethod
    def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> Dict:
        """
        Calculate EMI using standard formula:
        EMI = P * r * (1+r)^n / ((1+r)^n - 1)
        """
        if annual_rate == 0:
            emi = principal / tenure_months
            return {
                "emi": round(emi, 2),
                "total_payment": round(principal, 2),
                "total_interest": 0,
                "principal": principal,
                "schedule": [],
            }

        monthly_rate = annual_rate / (12 * 100)
        emi = principal * monthly_rate * math.pow(1 + monthly_rate, tenure_months) / (
            math.pow(1 + monthly_rate, tenure_months) - 1
        )

        total_payment = emi * tenure_months
        total_interest = total_payment - principal

        # Amortization schedule (first 6 + last 3 months for display)
        schedule = []
        balance = principal
        for month in range(1, tenure_months + 1):
            interest_component = balance * monthly_rate
            principal_component = emi - interest_component
            balance -= principal_component

            if month <= 6 or month > tenure_months - 3:
                schedule.append({
                    "month": month,
                    "emi": round(emi, 2),
                    "principal": round(principal_component, 2),
                    "interest": round(interest_component, 2),
                    "balance": round(max(balance, 0), 2),
                })

        return {
            "emi": round(emi, 2),
            "total_payment": round(total_payment, 2),
            "total_interest": round(total_interest, 2),
            "principal": principal,
            "annual_rate": annual_rate,
            "tenure_months": tenure_months,
            "interest_percentage": round((total_interest / total_payment) * 100, 1),
            "schedule": schedule,
        }

    # ── Budget Planner ─────────────────────────────────────────

    @staticmethod
    def budget_50_30_20(monthly_income: float) -> Dict:
        """Apply the 50-30-20 budgeting rule."""
        needs = monthly_income * 0.50
        wants = monthly_income * 0.30
        savings = monthly_income * 0.20

        return {
            "monthly_income": monthly_income,
            "needs": {
                "amount": round(needs, 2),
                "percentage": 50,
                "categories": [
                    {"name": "Rent/Housing", "suggested": round(needs * 0.40, 2)},
                    {"name": "Food & Groceries", "suggested": round(needs * 0.25, 2)},
                    {"name": "Transportation", "suggested": round(needs * 0.15, 2)},
                    {"name": "Utilities & Bills", "suggested": round(needs * 0.12, 2)},
                    {"name": "Healthcare", "suggested": round(needs * 0.08, 2)},
                ],
            },
            "wants": {
                "amount": round(wants, 2),
                "percentage": 30,
                "categories": [
                    {"name": "Entertainment", "suggested": round(wants * 0.33, 2)},
                    {"name": "Dining Out", "suggested": round(wants * 0.25, 2)},
                    {"name": "Shopping", "suggested": round(wants * 0.25, 2)},
                    {"name": "Hobbies", "suggested": round(wants * 0.17, 2)},
                ],
            },
            "savings": {
                "amount": round(savings, 2),
                "percentage": 20,
                "categories": [
                    {"name": "Emergency Fund", "suggested": round(savings * 0.25, 2)},
                    {"name": "Investments (SIP/PPF)", "suggested": round(savings * 0.40, 2)},
                    {"name": "Retirement (NPS)", "suggested": round(savings * 0.20, 2)},
                    {"name": "Insurance Premiums", "suggested": round(savings * 0.15, 2)},
                ],
            },
            "rule": "50-30-20",
            "tip": "An emergency fund should cover 3-6 months of expenses.",
        }

    # ── Financial Health Score ─────────────────────────────────

    @staticmethod
    def calculate_health_score(data: Dict) -> Dict:
        """
        Calculate financial health score (0-100).
        Factors: savings rate, debt ratio, emergency fund, insurance, investments.
        """
        score = 0
        insights = []
        recommendations = []

        income = float(data.get("monthly_income", 0))
        expenses = float(data.get("monthly_expenses", 0))
        savings = float(data.get("monthly_savings", 0))
        debt_emi = float(data.get("monthly_debt_emi", 0))
        emergency_fund = float(data.get("emergency_fund_months", 0))
        has_insurance = bool(data.get("has_insurance", False))
        has_investments = bool(data.get("has_investments", False))
        has_retirement = bool(data.get("has_retirement_savings", False))

        if income <= 0:
            return {"score": 0, "grade": "N/A", "insights": ["Please enter valid income"], "recommendations": []}

        # 1. Savings Rate (max 25 pts)
        savings_rate = (savings / income) * 100 if income > 0 else 0
        if savings_rate >= 20:
            score += 25
            insights.append("✅ Excellent savings rate of {:.0f}%".format(savings_rate))
        elif savings_rate >= 10:
            score += 15
            insights.append("✅ Good savings rate of {:.0f}%".format(savings_rate))
            recommendations.append("💡 Try to increase savings to 20% of income using SIP")
        else:
            score += max(0, int(savings_rate))
            insights.append("⚠️ Low savings rate of {:.0f}%".format(savings_rate))
            recommendations.append("🎯 Start with saving at least ₹500/month and increase gradually")

        # 2. Debt-to-Income Ratio (max 20 pts)
        dti = (debt_emi / income) * 100 if income > 0 else 0
        if dti == 0:
            score += 20
            insights.append("✅ No debt obligations – excellent!")
        elif dti <= 30:
            score += 15
            insights.append("✅ Healthy debt-to-income ratio of {:.0f}%".format(dti))
        elif dti <= 50:
            score += 8
            insights.append("⚠️ High debt ratio of {:.0f}%".format(dti))
            recommendations.append("💡 Focus on paying off high-interest loans first")
        else:
            score += 0
            insights.append("🚨 Dangerous debt ratio of {:.0f}% – take immediate action".format(dti))
            recommendations.append("🚨 Seek debt counseling; use MUDRA scheme for business restructuring")

        # 3. Emergency Fund (max 20 pts)
        if emergency_fund >= 6:
            score += 20
            insights.append("✅ Strong emergency fund of {:.0f} months".format(emergency_fund))
        elif emergency_fund >= 3:
            score += 12
            insights.append("✅ Emergency fund covers {:.0f} months".format(emergency_fund))
            recommendations.append("💡 Build emergency fund to 6 months of expenses")
        else:
            score += int(emergency_fund * 2)
            insights.append("⚠️ Emergency fund is too low ({:.0f} months)".format(emergency_fund))
            recommendations.append("🎯 Priority: Build emergency fund with liquid savings account/FD")

        # 4. Insurance (max 15 pts)
        if has_insurance:
            score += 15
            insights.append("✅ Insurance coverage in place")
        else:
            recommendations.append("🛡️ Get PMJJBY (₹436/year) and PMSBY (₹20/year) for basic coverage")

        # 5. Investments (max 10 pts)
        if has_investments:
            score += 10
            insights.append("✅ Investment portfolio active")
        else:
            recommendations.append("📈 Start a SIP with just ₹500/month in an index fund")

        # 6. Retirement Savings (max 10 pts)
        if has_retirement:
            score += 10
            insights.append("✅ Retirement savings in place (PPF/NPS)")
        else:
            recommendations.append("🏖️ Open an NPS account – get tax benefit under 80CCD(1B)")

        # Determine grade
        grade = "A+" if score >= 90 else "A" if score >= 80 else "B+" if score >= 70 \
            else "B" if score >= 60 else "C+" if score >= 50 else "C" if score >= 40 \
            else "D" if score >= 30 else "F"

        return {
            "score": min(score, 100),
            "grade": grade,
            "savings_rate": round(savings_rate, 1),
            "debt_to_income": round(dti, 1),
            "emergency_fund_months": emergency_fund,
            "insights": insights,
            "recommendations": recommendations[:5],
            "government_schemes": _get_relevant_schemes(score),
        }

    # ── SIP Calculator ─────────────────────────────────────────

    @staticmethod
    def calculate_sip(monthly_sip: float, annual_rate: float, years: int) -> Dict:
        """Calculate SIP returns."""
        monthly_rate = annual_rate / (12 * 100)
        n = years * 12
        future_value = monthly_sip * (math.pow(1 + monthly_rate, n) - 1) / monthly_rate * (1 + monthly_rate)
        invested = monthly_sip * n
        returns = future_value - invested

        return {
            "monthly_sip": monthly_sip,
            "annual_rate": annual_rate,
            "years": years,
            "future_value": round(future_value, 2),
            "total_invested": round(invested, 2),
            "estimated_returns": round(returns, 2),
            "wealth_gain_percentage": round((returns / invested) * 100, 1),
        }


def _get_relevant_schemes(score: int) -> List[Dict]:
    """Return relevant government schemes based on score."""
    schemes = []
    if score < 50:
        schemes.append({"name": "PMJDY", "desc": "Zero balance savings account with RuPay card", "url": "pmjdy.gov.in"})
        schemes.append({"name": "PMJJBY", "desc": "Life Insurance ₹2 lakh cover @ ₹436/year", "url": "jansuraksha.gov.in"})
    if score < 70:
        schemes.append({"name": "MUDRA Loan", "desc": "Loans up to ₹10 lakh for small businesses", "url": "mudra.org.in"})
        schemes.append({"name": "PPF", "desc": "Safe long-term savings with 7.1% tax-free returns", "url": "indiapost.gov.in"})
    schemes.append({"name": "NPS", "desc": "National Pension System – retirement savings with tax benefits", "url": "npscra.nsdl.co.in"})
    return schemes
