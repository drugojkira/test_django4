from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.db.models import Count
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import CreateCommentForm, CreatePostForm
from .models import Category, Comment, Post, User
from .mixins import CommentEditMixin, PostsEditMixin, PostsQuerySetMixin

PAGINATED_BY = 10


class PostDeleteView(PostsEditMixin, LoginRequiredMixin, DeleteView):
    model = Post
    success_url = reverse_lazy('blog:index')
    pk_url_kwarg = 'post_id'

    def delete(self, request, *args, **kwargs):
        post = get_object_or_404(Post, pk=self.kwargs['post_id'])
        if self.request.user != post.author:
            return redirect('blog:index')

        return super().delete(request, *args, **kwargs)


class PostUpdateView(PostsEditMixin, LoginRequiredMixin, UpdateView):
    form_class = CreatePostForm
    model = Post
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        post = get_object_or_404(Post, pk=self.kwargs['post_id'])
        if self.request.user != post.author:
            return redirect('blog:post_detail', pk=self.kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.kwargs
                                                   ['post_id']})


class PostCreateView(PostsEditMixin, LoginRequiredMixin, CreateView):
    model = Post
    form_class = CreatePostForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse(
            'blog:profile',
            kwargs={
                'username': self.request.user.username,
            },
        )


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CreateCommentForm

    def form_valid(self, form):
        form.instance.post = get_object_or_404(Post, pk=self.kwargs['post_id'])
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.kwargs
                                                   ['post_id']})


class CommentDeleteView(CommentEditMixin, LoginRequiredMixin, DeleteView):
    model = Comment
    pk_url_kwarg = 'comment_pk'

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.kwargs
                                                   ['post_id']})

    def delete(self, request, *args, **kwargs):
        comment = get_object_or_404(Comment, pk=self.kwargs['comment_pk'])
        if self.request.user != comment.author:
            return redirect('blog:post_detail', pk=self.kwargs['post_id'])
        return super().delete(request, *args, **kwargs)


class CommentUpdateView(CommentEditMixin, LoginRequiredMixin, UpdateView):
    model = Comment
    form_class = CreateCommentForm
    pk_url_kwarg = 'comment_pk'

    def dispatch(self, request, *args, **kwargs):
        comment = get_object_or_404(Comment, pk=self.kwargs['comment_pk'])
        if self.request.user != comment.author:
            return redirect('blog:post_detail', pk=self.kwargs['post_id'])

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.kwargs
                                                   ['post_id']})


class AuthorProfileListView(PostsQuerySetMixin, ListView):
    model = Post
    template_name = 'blog/profile.html'
    paginate_by = PAGINATED_BY

    def add_comment_count_annotation(self, queryset):
        return queryset.annotate(comment_count=Count('comments'))

    def get_queryset(self):
        if self.request.user.username == self.kwargs['username']:
            return (
                self.request.user.posts.select_related(
                    'category',
                    'author',
                    'location',
                )
                .all()
            )
        return self.add_comment_count_annotation(
            super().get_queryset().filter(author__username=self.kwargs
                                          ['username'])
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = get_object_or_404(
            User, username=self.kwargs['username']
        )
        return context


class BlogIndexListView(PostsQuerySetMixin, ListView):
    model = Post
    template_name = 'blog/index.html'
    context_object_name = 'post_list'
    paginate_by = PAGINATED_BY

    def add_comment_count_annotation(self, queryset):
        return queryset.annotate(comment_count=Count('comments'))

    def get_queryset(self):
        queryset = super().get_queryset().filter(category__is_published=True)
        return self.add_comment_count_annotation(queryset)


class BlogCategoryListView(PostsQuerySetMixin, ListView):
    model = Post
    template_name = 'blog/category.html'
    context_object_name = 'post_list'
    paginate_by = PAGINATED_BY

    def add_comment_count_annotation(self, queryset):
        return queryset.annotate(comment_count=Count('comments'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(
            Category, slug=self.kwargs['category_slug'], is_published=True
        )
        return context

    def get_queryset(self):
        return self.add_comment_count_annotation(
            super().get_queryset().filter(category__slug=self.kwargs
                                          ['category_slug'])
        )


class PostDetailView(PostsQuerySetMixin, DetailView):
    model = Post
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CreateCommentForm()
        context['comments'] = (
            self.get_object().comments.prefetch_related('author').all()
        )
        return context

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(
                'comments',
            )
        )

    def get_object(self, queryset=None):
        post = get_object_or_404(Post, pk=self.kwargs['post_id'])
        if self.request.user == post.author:
            return post
        return get_object_or_404(
            Post, is_published=True, category__is_published=True,
            pub_date__lt=timezone.now(), pk=self.kwargs['post_id'])
