from django.utils import timezone
from .models import Comment, Post


class PostsQuerySetMixin:
    def get_queryset(self):
        return Post.objects.filter(
            is_published=True,
            pub_date__lte=timezone.now()
        )


class PostsEditMixin:
    model = Post
    template_name = 'blog/create.html'
    queryset = Post.objects.select_related('author', 'location', 'category')


class CommentEditMixin:
    model = Comment
    pk_url_kwarg = 'comment_pk'
    template_name = 'blog/comment.html'
