class BaseAlertPlugin:
    def __init__(self, db_tool=None, yahoo_tool=None):
        self.db_tool = db_tool
        self.yahoo_tool = yahoo_tool

    def check_alerts(self) -> list:
        """
        Override this method in subclasses to return a list of triggered alert messages.
        """
        raise NotImplementedError("Plugin must implement `check_alerts` method.")
