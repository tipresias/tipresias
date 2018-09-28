class HomeController:
    """Controller root"""

    def show(self, View):  # pylint: disable=R0201
        """Show Welcome Template"""

        return View('/storage/compiled/index')  # pylint: disable=E0602
