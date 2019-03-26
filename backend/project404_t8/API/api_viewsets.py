from django.shortcuts import render
from rest_framework import generics,status,viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Post, Comment, Friendship, Follow, Server
from users.models import CustomUser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .serializers import UserSerializer, PostSerializer, CommentSerializer, FriendshipSerializer, FollowSerializer, ServerSerializer
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views import generic
from .forms import uploadForm, friendRequestForm, EditProfileForm, commentForm
from django.conf import settings
from users.models import CustomUser
from random import uniform
import json
from django.urls import reverse_lazy
from django.views.generic.edit import DeleteView, UpdateView
import API.services as Services
from rest_framework.exceptions import APIException, MethodNotAllowed, NotFound, PermissionDenied
from markdownx.utils import markdownify
from collections import OrderedDict

### Helper methods ###
# To help get data, and so we don't have to reuse code all the time
# What is request though in this context
# Rather, we might need to work around

# My biggest fear with these helper functions rn is how
# I'm modifying and accessing the request.path
# which makes it a new object or something
# IDK what it actually is doing, and I assume it is bad practice
# but as long as hostname information isnt lost along the way
# and security isn't compromised we should be good 

# Get author info
# extra is a boolean that returns list of friends as well as github,bio,etc.
# pk is the authors ID
def getAuthorData(request, extra=False, pk=None):
    
    # Modify the requests path
    request.path = "/author/" + pk

    queryset = CustomUser.objects.all()
    user = get_object_or_404(queryset, pk=pk)
    response = {}

    # build a list of friends for the response
    # This will be optional
    if extra:
        friends_list = []
        friends = Friendship.objects.filter(friend_a=user.id)
        for friend in friends:
            friend_entry = {}

            url = "https://" + request.get_host() + "/author/" + str(friend.friend_b.id) 
            friend_object = get_object_or_404(queryset, pk=friend.friend_b.id)

            friend_entry["id"] = url
            # todo: look up the user, find what host they belong to, and return that value
            # instead of using request.get_host() here
            friend_entry["host"] = "https://" + request.get_host() + "/" 
            friend_entry["displayName"] =  friend_object.displayname
            friend_entry["url"] = url
            friends_list.append(friend_entry)
        response["friends"] = friends_list

        # Optional info will also only be given if extra is selected
        if Services.isNotBlank(user.github_url):
            response["github"] = user.github_url
        if Services.isNotBlank(user.first_name):
            response["firstName"] = user.first_name
        if Services.isNotBlank(user.last_name):
            response["lastName"] = user.last_name
        if Services.isNotBlank(user.email):
            response["email"] = user.email
        if Services.isNotBlank(user.bio):
            response["bio"] = user.bio

    
    response["id"] = "http://" + request.get_host() + request.path
    response["host"] = request.get_host()
    response["displayName"] = user.displayname
    response["url"] = "http://" + request.get_host() + request.path
    
    return response

# Get comment information
# pk is the comment ID
def getCommentData(request, pk=None):
    # TODO do me big boy
    pass

# Get post information for a single post
# pk is the post ID
def getPostData(request, pk=None):

    # Modify the request path
    request.path = "/posts/" + pk

    # permission_classes = (IsAuthenticated,)
    queryset = Post.objects.filter(pk=pk)
    post = PostSerializer(queryset, many=True).data[0]
    
    # Init the returned dictionary
    currentPost = OrderedDict()

    # title
    title = post["title"]
    currentPost.update({"title":title})

    # source
    source = "TODO, what should this be?"
    currentPost.update({"source":source})

    # origin
    # just the path of the post
    origin = "TODO, this should be the post url"
    currentPost.update({"origin":origin})

    # description
    # we don't really have a description yet, what would we put
    description = "N/A"
    currentPost.update({"description":description})

    # contentType
    # How do we embed images
    contentType = "TODO, embedding images??"
    currentPost.update({"contentType":contentType})

    # content
    content = post["body"]
    currentPost.update({"content":content})

    # Get author information
    # Then add author to the dic
    authorId = str(post["author"])
    author = getAuthorData(request, extra=False, pk=authorId)
    currentPost.update({"author":author})
    
    # Get comment info
    # TODO peter you should be able to figure this out
    # Use the helper function you will make
    # This actually looks so tedious omg
    comments = []
    currentPost.update({"comments":comments})

    return currentPost




############ API Methods

class PostsPagination(PageNumberPagination):
    # change this to 50 later, currently at 1 for testing purposes
    page_size = 1
    page_size_query_param = 'size'
  
# https://www.django-rest-framework.org/api-guide/routers/
# https://www.django-rest-framework.org/api-guide/viewsets/#api-reference

class PostsViewSet(viewsets.ModelViewSet):
    http_method_names = ['get','post'] # only GETs allowed right now
    queryset = Post.objects.filter()
    serializer_class = PostSerializer

    # Instantiates and returns the list of permissions that this view requires.
    # This is useful if you only want some Posts URLs to require authentication but not others
    # def get_permissions(self):
    #     if self.action == 'list':
    #         permission_classes = []
    #     else:
    #         permission_classes = [IsAuthenticated]
    #     return [permission() for permission in permission_classes]

    # GET http://service/posts (all posts marked as public on the server)
    # Ok, this is gonna get real fucking nasty so read carefully
    # NVM, we are gonna modularize it
    def list(self, request):
        
        # Query <all> amount of public posts from the table
        # This can be done with django pagination framework somehow
        # But that can just be done later >:)
        # TODO Pagination shit here somehow
        queryset = Post.objects.filter(privacy_setting="6")

        # This serializes all the posts into an ordered dictionary
        # Hopefully only the amount requested
        serialized_posts = PostSerializer(queryset, many=True)
        # print(serialized_posts.data)

        # We don't want to use this one, the order is all messed up and shit
        # Although in theory the order shouldn't matter if they 
        # use a proper json parser
        # Anyways, we will create a new ordered dict
        # And make sure all the correct elements are added in order
        
        # Response is the bigboy json response at the end
        response = OrderedDict()

        # First is the meta data
        # "query":"posts"
        response.update({"query":"posts"})

        # count
        count = len(queryset)
        response.update({"count":count})

        # size
        # This is the size of what was requested
        # Default can be 50 for now or something
        size = "TODO"
        response.update({"size":size})

        # next
        next = "TODO"
        response.update({"next":next})

        # previous
        previous = "TODO"
        response.update({"previous":previous})

        # posts
        # loop through the retrieved posts (currently all of them)
        # and harness the data like a madman
        posts = []
        
        for post in serialized_posts.data:
            # Get single post information
            # print(post)
            postId = str(post["id"])            
            posts.append(getPostData(request, pk=postId))


        response.update({"posts":posts})
    
        # Finally, return this huge mfer
        return Response(response)
    
    # GET http://service/posts/{POST_ID} access to a single post with id = {POST_ID}
    def retrieve(self, request, pk=None):
        # permission_classes = (IsAuthenticated,)
        queryset = Post.objects.filter(pk=pk)
        serializer_class = PostSerializer(queryset, many=True)
        return Response(serializer_class.data)
    
    # the API endpoint accessible at GET http://service/posts/{post_id}/comments
    @action(methods=['get','post'], detail=True, url_path="comments")
    def userPostComments(self, request, pk=None):
        post_id = pk
        requested_post = Post.objects.get(id=post_id)
        if request.method =="POST":
            # we're allowed to see the post - for now just check if the posts are public
            if requested_post.privacy_setting == "6": 
                queryset = Comment.objects.filter(post=post_id)
                serializer_class = CommentSerializer(queryset, many=True)
                return Response(serializer_class.data)
            else:
                # for now, raise an exception if the post we want to see isn't set to Public
                # this will have to be changed later
                raise PermissionDenied("Forbidden: The post you wished to access comments for is not Public")

        else: # this handles "GET" methods

            # we're allowed to see the post - for now just check if the posts are public
            if requested_post.privacy_setting == "6": 
                queryset = Comment.objects.filter(post=post_id)
                serializer_class = CommentSerializer(queryset, many=True)
                return Response(serializer_class.data)
            else: 
                # for now, raise an exception if the post we want to see isn't set to Public
                # this will have to be changed later
                raise PermissionDenied("Forbidden: The post you wished to access comments for is not Public")



    

class AuthorViewSet(viewsets.ModelViewSet):
    # http_method_names = ['get', 'post', 'head'] # specify which types of requests are allowed
    permission_classes = (IsAuthenticated,)
    queryset = CustomUser.objects.filter()
    pagination_class = PostsPagination
    serializer_class = UserSerializer

    # we don't want there to be any functionality for GET http://service/author 
    def list(self, request):
        raise NotFound()

    # we don't want there to be any functionality for GET http://service/author
    def create(self, request):
        raise NotFound()

    # GET http://service/author/{author_id}
    # returns information about the author
    def retrieve(self, request, pk=None):
        queryset = CustomUser.objects.all()
        user = get_object_or_404(queryset, pk=pk)
        # paginator = PostsPagination()
        # posts = paginator.paginate_queryset(queryset, request)

        # build a list of friends for the response
        friends_list = []
        friends = Friendship.objects.filter(friend_a=user.id)
        for friend in friends:
            friend_entry = {}

            url = "https://" + request.get_host() + "/author/" + str(friend.friend_b.id) 
            friend_object = get_object_or_404(queryset, pk=friend.friend_b.id)

            friend_entry["id"] = url
            # todo: look up the user, find what host they belong to, and return that value
            # instead of using request.get_host() here
            friend_entry["host"] = "https://" + request.get_host() + "/" 
            friend_entry["displayName"] =  friend_object.displayname
            friend_entry["url"] = url
            friends_list.append(friend_entry)

        response = {}
        response["id"] = "http://" + request.get_host() + request.get_full_path()
        response["host"] = request.get_host()
        response["displayName"] = user.displayname
        response["url"] = "http://" + request.get_host() + request.get_full_path()
        response["friends"] = friends_list
        if Services.isNotBlank(user.github_url):
            response["github"] = user.github_url
        if Services.isNotBlank(user.first_name):
            response["firstName"] = user.first_name
        if Services.isNotBlank(user.last_name):
            response["lastName"] = user.last_name
        if Services.isNotBlank(user.email):
            response["email"] = user.email
        if Services.isNotBlank(user.bio):
            response["bio"] = user.bio

        return Response(response)

    # http://service/author/posts (posts that are visible to the currently authenticated user)
    @action(methods=['get'], detail=False)
    def posts(self, request, pk=None):
        uname = request.user
        uid = uname.id
        # todo: properly escape this using https://docs.djangoproject.com/en/1.9/topics/db/sql/#passing-parameters-into-raw
        allowed_posts = Post.objects.raw(' \
        WITH posts AS (SELECT id FROM API_post WHERE author_id in  \
        (SELECT f2.friend_a_id AS fofid \
            FROM API_friendship f \
            JOIN API_friendship f2 ON f.friend_a_id = f2.friend_b_id \
            WHERE fofid NOT IN (SELECT friend_a_ID FROM API_friendship  \
            WHERE friend_b_id = %s) AND f.friend_b_id = %s AND fofid != %s) AND privacy_setting = 4 \
        UNION \
            SELECT id FROM API_post WHERE (author_id in  \
            (WITH friends(fid) AS (SELECT friend_b_id FROM API_friendship WHERE friend_a_id=%s) \
            SELECT * FROM friends WHERE fid != %s GROUP BY fid)  \
            AND (privacy_setting = 3 OR privacy_setting = 4)) OR author_id = %s OR  privacy_setting = 6) \
            SELECT * FROM API_post WHERE id in posts', [int(uid)]*6)

        serializer_class = PostSerializer(allowed_posts, many=True)
        return Response(serializer_class.data)

    # the API endpoint accessible at GET http://service/author/{author_id}/posts
    # Can't name this method "posts" because there's already a "posts" method above
    # so I had to add this @action tag stuff
    @action(methods=['get'], detail=True, url_path="posts")
    def userPosts(self, request, pk=None):
        author_id = int(self.kwargs['pk'])
        uname = request.user
        uid = uname.id
        allowed_posts = Post.objects.raw(' \
        WITH posts AS (SELECT id FROM API_post WHERE author_id in  \
        (SELECT f2.friend_a_id AS fofid \
            FROM API_friendship f \
            JOIN API_friendship f2 ON f.friend_a_id = f2.friend_b_id \
            WHERE fofid NOT IN (SELECT friend_a_ID FROM API_friendship  \
            WHERE friend_b_id = %s) AND f.friend_b_id = %s AND fofid != %s) AND privacy_setting = 4 \
        UNION \
            SELECT id FROM API_post WHERE (author_id in  \
            (WITH friends(fid) AS (SELECT friend_b_id FROM API_friendship WHERE friend_a_id=%s) \
            SELECT * FROM friends WHERE fid != %s GROUP BY fid)  \
            AND (privacy_setting = 3 OR privacy_setting = 4)) OR author_id = %s OR  privacy_setting = 6) \
            SELECT * FROM API_post WHERE id in posts \
            AND author_id = %s', [int(uid)]*6 + [author_id])

        paginator = PostsPagination()
        paginated_posts = paginator.paginate_queryset(allowed_posts, request)
        serializer_class = PostSerializer(paginated_posts, many=True)
        # print(Services.get_page_size(request, paginator))
        # is returning none for next/previous okay, or do I need to not return anything
        response = {
            "query": "posts",
            "count": len(allowed_posts),
            "size": Services.get_page_size(request, paginator),
            "next": None,
            "previous": None,
            "posts" : serializer_class.data,
        }

        if paginator.get_next_link() is not None:
            response["next"] = paginator.get_next_link()
        if paginator.get_previous_link() is not None:
            response["previous"] = paginator.get_previous_link()
        # print(paginator.get_next_link())
        return Response(response)

    # the API endpoint accessible at GET http://service/author/<authorid>/friends/
    # returns the author's friend list
    # TODO rename this function, its got a duplicate name basically
    @action(methods=['get'], detail=True, url_path="friends")
    def userFriends(self, request, pk=None):
        author_id = pk
        # since the friendship table is 2-way, request a list of users whose 
        # IDs are in the friendship table, not including the author
        # make sure to format this the appropriate way
        friendship_authors = []
        friends = Friendship.objects.filter(friend_a=author_id)
        
        for friend in friends:
            url = "https://" + request.get_host() + "/author/" + str(friend.friend_b.id) 
            friendship_authors.append(url)
    
        # serialize friendship_authors here
        friendship_dict = {}
        friendship_dict["query"] = "friends"
        friendship_dict["author"] = pk
        friendship_dict["authors"] = friendship_authors
    
        # return serialized friendship_authors
        return Response(friendship_dict)
    @action(methods=['get'], detail=True, url_path="friends/(?P<author_id2>\d+)")
    def friends(self, request, pk=None,author_id2=None):
        author_id = pk
                # since the friendship table is 2-way, request a list of users whose 
        # IDs are in the friendship table, not including the author
        # make sure to format this the appropriate way
        if request.method == "GET":
            friendship_authors = []
            friends = Friendship.objects.filter(friend_a=author_id, friend_b=author_id2)
            friendship_dict = {}
            if friends:
                for friend in friends:
                    url = "https://" + request.get_host() + "/author/" + str(friend.friend_a.id) 
                    url2 = "https://" + request.get_host() + "/author/" + str(friend.friend_b.id) 
                    friendship_authors.append(url)
                    friendship_authors.append(url2)
                friendship_dict["friends"]= True
            else:
                for friend in friends:
                    url = "https://" + request.get_host() + "/author/" + str(friend.friend_a.id) 
                    url2 = "https://" + request.get_host() + "/author/" + str(friend.friend_b.id) 
                    friendship_authors.append(url)
                    friendship_authors.append(url2)
                
                friendship_dict["friends"]= False
        
            # serialize friendship_authors here
            friendship_dict["query"] = "friends"
            friendship_dict["authors"] = friendship_authors

            return Response(friendship_dict)
            
        else: 
             friends = Friendship.objects.filter(friend_a=author_id)









    
