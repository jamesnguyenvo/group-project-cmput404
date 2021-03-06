from rest_framework import routers
import API.viewsets as Viewsets

# these are the API methods
api_router = routers.SimpleRouter(trailing_slash=False)
api_router.register(r'posts', Viewsets.PostsViewSet)
api_router.register(r'author', Viewsets.AuthorViewSet)
api_router.register(r'friendrequest', Viewsets.FriendRequestViewSet)

