''' Web Routes '''
from masonite.routes import Get, Post

ROUTES = [
    Get().route('/', 'HomeController@show').name('home'),
]
