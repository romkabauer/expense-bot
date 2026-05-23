from abc import abstractmethod
from asyncio import gather, sleep
import os
import json
import secrets
import requests as r
import tempfile
import time

from logger import Logger


class GenericBIInterface:
    def __init__(self):
        self.service_user_name = ...
        self.service_user_pass = ...

    @abstractmethod
    def get_auth_token(self):
        raise NotImplementedError


class SupersetInterface(GenericBIInterface):
    def __init__(self, logger: Logger | None = None) -> None:
        super().__init__()
        self.base_url = os.getenv("SUPERSET_BASE_URL")
        self.service_user_name = os.getenv("SUPERSET_ADMIN_USERNAME")
        self.service_user_pass = os.getenv("SUPERSET_ADMIN_PASSWORD")
        self.superset_ui_url = os.getenv("SUPERSET_UI_URL")

        self.session = r.Session()
        self.logger = logger

        self.auth_token = self.__get_auth_token()
        self.csrf_token = self.__get_csrf_token()

        self.default_viewer_permission_scope = [
            {
                "permission_name": "can_read",
                "view_menu_name": "Chart"
            },
            {
                "permission_name": "can_read",
                "view_menu_name": "Dataset"
            },
            {
                "permission_name": "can_read",
                "view_menu_name": "Dashboard"
            },
            {
                "permission_name": "can_recent_activity",
                "view_menu_name": "Log"
            },
            {
                "permission_name": "menu_access",
                "view_menu_name": "Dashboards"
            },
            {
                "permission_name": "menu_access",
                "view_menu_name": "Charts"
            },
            {
                "permission_name": "datasource_access",
                "view_menu_name": "[ExpenseBot].[expenses](id:1)"
            },
            {
                "permission_name": "can_this_form_post",
                "view_menu_name": "ResetMyPasswordView"
            },
            {
                "permission_name": "can_this_form_get",
                "view_menu_name": "ResetMyPasswordView"
            },
            {
                "permission_name": "can_userinfo",
                "view_menu_name": "UserDBModelView"
            },
            {
                "permission_name": "resetmypassword",
                "view_menu_name": "UserDBModelView"
            },
            {
                "permission_name": "can_info",
                "view_menu_name": "User"
            },
            {
                "permission_name": "can_time_range",
                "view_menu_name": "Api"
            },
        ]

    async def create_user_with_custom_role(self, user_id: int) -> str:
        _, custom_role_id, superset_pass = await self.__create_user(user_id)
        await self.__create_rls_policy(user_id, custom_role_id)
        return superset_pass

    async def reset_user(self, user_id: int) -> str:
        if await self.is_user_exist(user_id):
            u_id = await self.__get_internal_entity_id_by_name("users", {
                    "col": "username",
                    "opr": "eq",
                    "value": f"user_{user_id}"
                })
            self.session.delete(url=f"{self.base_url}/security/users/{u_id}",
                                headers={
                                    "accept": "application/json",
                                    "Content-Type": "application/json",
                                    "Authorization": f"Bearer {self.auth_token}"
                                })
            role_id = await self.__get_internal_entity_id_by_name("roles", {
                    "col": "name",
                    "opr": "eq",
                    "value": f"user_{user_id}"
                })
            self.session.delete(url=f"{self.base_url}/security/roles/{role_id}",
                                headers={
                                    "accept": "application/json",
                                    "Content-Type": "application/json",
                                    "Authorization": f"Bearer {self.auth_token}"
                                })
            rls_id = await self.__get_internal_entity_id_by_name("rowlevelsecurity", {
                    "col": "name",
                    "opr": "eq",
                    "value": f"user_{user_id}"
                })
            self.session.delete(url=f"{self.base_url}/rowlevelsecurity/{rls_id}",
                                headers={
                                    "accept": "application/json",
                                    "Content-Type": "application/json",
                                    "Authorization": f"Bearer {self.auth_token}",
                                    'X-CSRFToken': self.csrf_token
                                })

        return await self.create_user_with_custom_role(user_id)

    async def is_user_exist(self, user_id: int) -> bool:
        try:
            superset_user_id = await self.__get_internal_entity_id_by_name("users", {
                "col": "username",
                "opr": "eq",
                "value": f"user_{user_id}"
            })
            if not superset_user_id:
                return False
        except Exception as e:
            raise ConnectionError(f"Error occurred while checking user existence: {e}")
        return True if superset_user_id else False

    def __get_auth_token(self) -> str:
        data = json.dumps({
            "password": self.service_user_pass,
            "provider": "db",
            "refresh": True,
            "username": self.service_user_name
        })
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        response = self.session.post(url=f"{self.base_url}/security/login", headers=headers, data=data)
        if response.status_code != 200:
            raise ConnectionError(f"Authorization to SuperSet failed: {response.text}")
        return response.json()["access_token"]

    def __get_csrf_token(self) -> str:
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}"
        }

        response = self.session.get(url=f"{self.base_url}/security/csrf_token", headers=headers)
        if response.status_code != 200:
            raise ConnectionError(f"Get CSRF token failed: {response.text}")
        return response.json()["result"]

    async def __get_viewer_permission_ids(self):
        permission_ids_coroutines = []
        for permission_scope in self.default_viewer_permission_scope:
            permission_id_coroutine = self.__get_permission_resource_id(
                permission_scope["permission_name"],
                permission_scope["view_menu_name"]
            )
            permission_ids_coroutines.append(permission_id_coroutine)
        ids = await gather(*permission_ids_coroutines)
        return ids

    async def __get_permission_resource_id(self, permission_name: str, resource_name: str):
        permission_id = await self.__get_internal_entity_id_by_name(
            "permissions",
            {
                "col": "name",
                "opr": "eq",
                "value": permission_name
            }
        )
        resource_id = await self.__get_internal_entity_id_by_name(
            "resources",
            {
                "col": "name",
                "opr": "eq",
                "value": resource_name
            }
        )
        permission_resource_map_id = await self.__get_internal_entity_id_by_name(
            "permissions-resources",
            {
                "col": "permission",
                "opr": "rel_o_m",
                "value": permission_id
            },
            {
                "col": "view_menu",
                "opr": "rel_o_m",
                "value": resource_id
            },
        )
        return permission_resource_map_id

    async def __get_internal_entity_id_by_name(self,
                                               entity_type: str,
                                               *filters: dict[str, str | int]):
        """
        :param entity_type: Could be 'permissions', 'resources' or 'permissions-resources'
        :param filters: Each filter has the following structure {
            "col": "col_name",
            "opr": "operator_string", # most frequent "eq", "rel_o_m"
            "value": "int_value" # or int_value
        }"""
        params = {
            "q": json.dumps({"filters": [*filters]})
        }
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.auth_token}"
        }
        if entity_type == 'rowlevelsecurity':
            headers['X-CSRFToken'] = self.csrf_token

        response = self.session.get(
            url=(f"{self.base_url}/"
                 f"{'security/' if not entity_type == 'rowlevelsecurity' else ''}"
                 f"{entity_type}/"),
            headers=headers,
            params=params
        )
        if response.status_code != 200:
            raise ConnectionError(f"Unable to fetch permission info: {response.text}")
        try:
            result = response.json()["result"]
            if len(result) == 0:
                return None
            permission_id = result[0]["id"]
        except KeyError as ke:
            raise KeyError(f"Key 'id' was not found in the Superset payload: {ke}")
        except Exception as e:
            raise ConnectionError(f"Unable to fetch permission info: {e}")
        return permission_id

    async def __create_security_role(self, user_id: int) -> int:
        """Create security role and get id of created role back"""
        data = json.dumps({
            "name": f"user_{user_id}"
        })
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}"
        }

        response = self.session.post(url=f"{self.base_url}/security/roles", headers=headers, data=data)
        if response.status_code != 201:
            raise ConnectionError(f"Role creation for user {user_id} failed: {response.text}")
        role_id = response.json()["id"]
        await self.__assign_base_security_scope_to_role(role_id)
        return role_id

    async def __assign_base_security_scope_to_role(self, role_id: int):
        data = json.dumps({
            "permission_view_menu_ids": await self.__get_viewer_permission_ids()
        })
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}"
        }
        response = self.session.post(
            url=f"{self.base_url}/security/roles/{role_id}/permissions",
            headers=headers,
            data=data
        )
        if response.status_code != 200:
            raise ConnectionError(f"Permissions for {role_id} was not added: {response.text}")
        return

    async def __create_user(self, user_id: int) -> tuple[int, int, str]:
        """Create user and get back id of new user back"""
        random_pass = secrets.token_urlsafe(8)
        security_role = await self.__create_security_role(user_id)
        data = json.dumps({
            "active": True,
            "email": f"user_{user_id}@localhost",
            "first_name": f"user_{user_id}",
            "last_name": f"user_{user_id}",
            "password": random_pass,
            "roles": [
                security_role
            ],
            "username": f"user_{user_id}"
        })
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}"
        }

        response = self.session.post(url=f"{self.base_url}/security/users", headers=headers, data=data)
        if response.status_code != 201:
            raise ConnectionError(f"Superset user creation for user {user_id} failed: {response.text}")
        return response.json()["id"], security_role, random_pass

    async def __create_rls_policy(self, user_id: int, role_id: int):
        data = json.dumps({
          "clause": f"user_id={user_id}",
          "filter_type": "Regular",
          "name": f"user_{user_id}",
          "roles": [
            role_id
          ],
          "tables": [
            1
          ]
        })
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
            "X-CSRFToken": self.csrf_token
        }
        response = self.session.post(url=f"{self.base_url}/rowlevelsecurity", headers=headers, data=data)
        if response.status_code != 201:
            raise ConnectionError(f"RLS policy creation for user {user_id} failed: {response.text}")

    def __build_user_data_mask(
            self,
            filter_name: str,
            column_name: str,
            target_value: int | str,
            dashboard_info: dict | None = None
        ) -> dict:
        """Helper to structure the native filter payload required by Superset v5."""
        filter_id = None

        if dashboard_info:
            json_metadata_str = dashboard_info.get("json_metadata")

            if json_metadata_str:
                try:
                    metadata = json.loads(json_metadata_str)
                    filter_configs = metadata.get("native_filter_configuration", [])

                    for config in filter_configs:
                        if config.get("name") == filter_name:
                            filter_id = config.get("id")
                            break
                except (json.JSONDecodeError, TypeError) as e:
                    self.logger.log("__build_user_data_mask", extra_text=f"Failed to get native filter{e}")
                    pass

        return {
            "dataMask": {
                filter_id: {
                    "id": filter_id,
                    "extraFormData": {
                        "filters": [
                            {
                                "col": column_name,
                                "op": "==",
                                "val": target_value
                            }
                        ]
                    },
                    "filterState": {
                        "value": [target_value]
                    }
                }
            }
        }

    async def __poll_for_screenshot(self, dashboard_id: str, cache_key: str, headers: dict, max_retries: int = 5) -> bytes:
        """Helper method to handle asynchronous polling of the screenshot generation."""
        screenshot_url = f"{self.base_url}/dashboard/{dashboard_id}/screenshot/{cache_key}/"

        for attempt in range(max_retries):
            await sleep(3)

            response = self.session.get(url=screenshot_url, headers=headers)
            if response.status_code == 200:
                return response.content

        raise ConnectionError(f"Superset worker timed out rendering image for cache key {cache_key}")

    async def __get_dashboard_info_by_name(self, dashboard_name: str) -> dict | None:
        """
        Lookup dashboard_id by dashboard_title
        :param dashboard_name: The visual Title of the dashboard in Superset
        :return: dashboard_id or None if not found
        """
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
            "X-CSRFToken": self.csrf_token
        }
        params = {
            "q": json.dumps(
                {
                    "filters": [{
                        "col": "dashboard_title",
                        "opr": "eq",
                        "value": dashboard_name
                    }],
                    "columns": ["id"],
                })
        }

        try:
            response = self.session.get(
                url=f"{self.base_url}/dashboard",
                headers=headers,
                params=params
            )

            if response.status_code != 200:
                raise ConnectionError(f"Failed to lookup dashboard: {response.text}")

            dashboard_id = None
            result = response.json().get("result", [])
            if result:
                dashboard_id = result[0]["id"]

                detail_response = self.session.get(
                    url=f"{self.base_url}/dashboard/{dashboard_id}",
                    headers=headers,
                )

                if detail_response.status_code != 200:
                    raise ConnectionError(f"Failed to fetch dashboard details: {detail_response.text}")

                detail_result = detail_response.json().get("result", [])
                if detail_result:
                    return detail_result

            return None
        except Exception as e:
            raise ConnectionError(f"Error looking up dashboard '{dashboard_name}': {e}")


    async def get_dashboard_image(
        self,
        dashboard_id_or_slug: str | int,
        target_user_id: int | str,
        user_native_filter_name: str = "User ID",
        column_name: str = "user_id",
        filename: str | None = None
    ) -> str:
        """
        Generates an on-the-fly filtered image of the hidden dashboard.
        Leverages URL parameters to bypass query cache engines (Cache Busting).

        :param dashboard_id_or_slug: The hidden dashboard containing your isolated target chart
        :param target_user_id: The user identity to fetch data for
        :param filter_id: The programmatic ID of your dashboard's native dashboard filter
        :param column_name: The database table column name mapping to user identity
        :param filename: Optional custom path to store file. Otherwise saved to a temp file
        :return: String path to the written PNG image
        """
        from urllib.parse import quote

        dashboard_id = str(dashboard_id_or_slug)
        dashboard_info = None
        if isinstance(dashboard_id_or_slug, str) and not dashboard_id_or_slug.isdigit() and "-" not in dashboard_id_or_slug:
            dashboard_info = await self.__get_dashboard_info_by_name(dashboard_id_or_slug)
            resolved_id = dashboard_info["id"]
            if not resolved_id:
                raise ConnectionError(f"Dashboard named '{dashboard_id_or_slug}' could not be resolved to an ID.")
            dashboard_id = str(resolved_id)

        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-CSRFToken": self.csrf_token,
        }

        # Structure payload and inject URL parameters for database query cache busting
        json_payload = self.__build_user_data_mask(
            user_native_filter_name,
            column_name,
            target_user_id,
            dashboard_info=dashboard_info
        )
        json_payload["urlParams"] = [
            ("force", "true"),
            ("_cb", str(int(time.time()))),
        ]

        request_body = {
            **json_payload,
        }

        try:
            # 1. Trigger the cache generation
            cache_url = f"{self.base_url}/dashboard/{dashboard_id}/cache_dashboard_screenshot/"
            cache_response = self.session.post(
                url=cache_url,
                headers=headers,
                json=request_body,
                params={"q":"(window_size:!(1200,800))"}
            )

            if cache_response.status_code != 202 and cache_response.status_code != 200:
                raise ConnectionError(f"Failed to initialize dashboard screenshot cache: {cache_response.text}")

            cache_key = cache_response.json().get("cache_key")
            if not cache_key:
                raise ValueError("Payload missing cache digest verification key.")

            # 2. Poll & fetch the completed binary data
            headers_download = {"Authorization": f"Bearer {self.auth_token}", "Accept": "image/png"}
            image_bytes = await self.__poll_for_screenshot(dashboard_id, cache_key, headers_download)

            # 3. Write binary data out to filesystem disk
            if filename:
                output_path = filename
            else:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                output_path = temp_file.name
                temp_file.close()

            with open(output_path, "wb") as f:
                f.write(image_bytes)

            return output_path

        except Exception as e:
            raise ConnectionError(f"Failed to pull filtered invisible dashboard context image: {e}")
