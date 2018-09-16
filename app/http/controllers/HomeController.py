''' Welcome The User To Masonite '''

class HomeController:
    ''' Controller For Welcoming The User '''

    def show(self):
        ''' Show Welcome Template '''
        return view('/storage/compiled/index')
