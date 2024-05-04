import os
from datetime import datetime as dt
import requests as r

import freecurrencyapi as fca


class CurrencyRateExtractor:
    def __init__(self,
                 supported_currencies: list[str],
                 base_currency: str = "USD",
                 on_date: str = dt.date(dt.now()).isoformat()):
        self.supported_currencies = supported_currencies
        self.base_currency = base_currency
        self.on_date = on_date
        if dt.fromisoformat(self.on_date) > dt.now():
            self.on_date = dt.date(dt.now()).isoformat()

    def extract_currency_rates(self) -> dict[str, str | dict[str, float]]:
        cdn_jsdelivr_rates = self.__extract_from_cdn_jsdelivr_api()
        if cdn_jsdelivr_rates.get("error_details"):
            freecurrencyapi_rates = self.__extract_from_freecurrency_api()
            if freecurrencyapi_rates.get("error_details"):
                return {
                    "base": self.base_currency,
                    "rates": {c: 0 for c in self.supported_currencies}
                }
            return freecurrencyapi_rates
        return cdn_jsdelivr_rates

    def __extract_from_freecurrency_api(self) -> dict[str, str | dict[str, float]]:
        api_key = os.getenv("FREECURRENCYAPI_API_KEY")
        client = fca.Client(api_key=api_key)
        try:
            currency_rate = client.latest(self.base_currency)['data'] \
                if self.on_date == dt.date(dt.now()).isoformat() \
                else list(
                    client.historical(
                        date=self.on_date,
                        base_currency=self.base_currency
                    )['data'].values()
                )[0]
        except Exception as e:
            return {
                "error_details": str(e)
            }
        return {
            "base": self.base_currency,
            "rates": currency_rate
        }

    def __extract_from_cdn_jsdelivr_api(self) -> dict[str, str | dict[str, float]]:
        """Docs: https://github.com/fawazahmed0/exchange-api?tab=readme-ov-file"""

        main_url = f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{self.on_date}/v1/currencies/{self.base_currency.lower()}.json"
        fallback_url = f"https://{self.on_date}.currency-api.pages.dev/v1/currencies/{self.base_currency.lower()}.json"

        try:
            res = r.get(main_url)
            raw_rates = res.json()
            rates = {k.upper(): v for k, v in raw_rates[self.base_currency.lower()].items()}
        except Exception as e:
            try:
                res = r.get(fallback_url)
                raw_rates = res.json()
                rates = {k.upper(): v for k, v in raw_rates[self.base_currency.lower()].items()}
            except Exception as e:
                return {
                    "error_details": str(e)
                }
        return {"base": self.base_currency, "rates": rates}

    def __extract_from_vatcomply_api(self) -> dict[str, str | dict[str, float]]:
        # DEPRECATED
        params = {
            "base": self.base_currency,
            "date": self.on_date
        }
        try:
            res = r.get(url="https://api.vatcomply.com/rates", params=params)
            rates = res.json()
        except Exception as e:
            return {
                "error_details": str(e)
            }
        return {"base": rates["base"], "rates": rates["rates"]}
