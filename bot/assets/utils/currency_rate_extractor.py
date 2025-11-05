import os
from datetime import datetime as dt
import requests as r

import freecurrencyapi as fca

from static import SUPPORTED_BASE_CURRENCIES


class CurrencyRateExtractor:
    def __init__(self):
        self.supported_currencies = SUPPORTED_BASE_CURRENCIES

    def extract_currency_rates(
            self,
            base_currency: str = "USD",
            on_date: str = dt.date(dt.now()).isoformat()) -> dict[str, str | dict[str, float]]:
        cdn_jsdelivr_rates = self.__extract_from_cdn_jsdelivr_api(base_currency, on_date)
        if "error_details" in cdn_jsdelivr_rates:
            freecurrencyapi_rates = self.__extract_from_freecurrency_api(base_currency, on_date)
            if "error_details" in freecurrencyapi_rates:
                return {
                    "base": base_currency,
                    "rates": {c: 0 for c in self.supported_currencies}
                }
            return freecurrencyapi_rates
        return cdn_jsdelivr_rates

    @staticmethod
    def __extract_from_freecurrency_api(
            base_currency: str = "USD",
            on_date: str = dt.date(dt.now()).isoformat()) -> dict[str, str | dict[str, float]]:
        api_key = os.getenv("FREECURRENCYAPI_API_KEY")
        client = fca.Client(api_key=api_key)
        try:
            currency_rate = client.latest(base_currency)['data'] \
                if on_date == dt.date(dt.now()).isoformat() \
                else list(
                    client.historical(
                        date=on_date,
                        base_currency=base_currency
                    )['data'].values()
                )[0]
        except Exception as e:
            return {
                "error_details": str(e)
            }
        return {
            "base": base_currency,
            "rates": currency_rate
        }

    @staticmethod
    def __extract_from_cdn_jsdelivr_api(
            base_currency: str = "USD",
            on_date: str = dt.date(dt.now()).isoformat()) -> dict[str, str | dict[str, float]]:
        """Docs: https://github.com/fawazahmed0/exchange-api?tab=readme-ov-file"""

        main_url = (f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@"
                    f"{on_date}/v1/currencies/{base_currency.lower()}.json")
        fallback_url = (f"https://{on_date}.currency-api.pages.dev/v1/currencies/"
                        f"{base_currency.lower()}.json")

        try:
            res = r.get(main_url, timeout=10)
            raw_rates = res.json()
            rates = {k.upper(): v for k, v in raw_rates[base_currency.lower()].items()}
        except Exception:
            try:
                res = r.get(fallback_url, timeout=10)
                raw_rates = res.json()
                rates = {k.upper(): v for k, v in raw_rates[base_currency.lower()].items()}
            except Exception as e:
                return {
                    "error_details": str(e)
                }
        return {"base": base_currency, "rates": rates}

    @staticmethod
    def __extract_from_vatcomply_api(
            base_currency: str = "USD",
            on_date: str = dt.date(dt.now()).isoformat()) -> dict[str, str | dict[str, float]]:
        # DEPRECATED
        params = {
            "base": base_currency,
            "date": on_date
        }
        try:
            res = r.get(url="https://api.vatcomply.com/rates", params=params, timeout=10)
            rates = res.json()
        except Exception as e:
            return {
                "error_details": str(e)
            }
        return {"base": rates["base"], "rates": rates["rates"]}
