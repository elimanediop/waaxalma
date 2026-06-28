class BaseAgent:
    name: str = "base-agent"
    description: str = "Base Waaxalma agent"

    def info(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
        }