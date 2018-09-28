''' Web Routes '''

from masonite.routes import Get, RouteGroup

ROUTES = [
    Get().route('/', 'HomeController@show').name('home'),
    # Using RouteGroup in anticipation of other API routes, but may be unnecesary
    RouteGroup(
        [Get().route('/predictions', 'ApiController@predictions').name('predictions')],
        prefix='/api',
        name='api'
    )
]
