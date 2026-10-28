from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CustomerBearerScheme(OpenApiAuthenticationExtension):
    target_class = "api.authentication.CustomerBearerAuthentication"
    name = "CustomerBearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "Customer API token",
        }
