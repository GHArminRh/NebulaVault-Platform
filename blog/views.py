from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Customer
from comment.models import Comment, CommentSettings, React, Reaction
from .models import BlogPost, BlogPostRating, Tag


def _published_posts():
    return BlogPost.objects.filter(
        status=BlogPost.Status.PUBLISHED,
        published_at__lte=timezone.now(),
    ).prefetch_related("tags")


def post_list(request):
    posts = _published_posts()
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    tag_id = request.GET.get("tag", "").strip()
    selected_tag = None
    if query:
        posts = posts.filter(
            Q(title__icontains=query)
            | Q(excerpt__icontains=query)
            | Q(content__icontains=query)
            | Q(tags__name__icontains=query)
        ).distinct()
    if category:
        posts = posts.filter(category=category)
    if tag_id:
        selected_tag = get_object_or_404(Tag, pk=tag_id)
        posts = posts.filter(tags=selected_tag)
    categories = (
        _published_posts().exclude(category="")
        .values_list("category", flat=True).distinct()
    )
    tags = Tag.objects.filter(posts__status=BlogPost.Status.PUBLISHED,
                              posts__published_at__lte=timezone.now()).distinct()
    page_obj = Paginator(posts, 9).get_page(request.GET.get("page"))
    return render(request, "blog/post_list.html", {
        "posts": page_obj.object_list,
        "page_obj": page_obj,
        "query": query,
        "selected_category": category,
        "categories": categories,
        "tags": tags,
        "selected_tag": selected_tag,
    })


def tag_list(request, tag_id):
    tag = get_object_or_404(Tag, pk=tag_id)
    posts = _published_posts().filter(tags=tag)
    page_obj = Paginator(posts, 9).get_page(request.GET.get("page"))
    tags = Tag.objects.filter(posts__status=BlogPost.Status.PUBLISHED,
                              posts__published_at__lte=timezone.now()).distinct()
    categories = _published_posts().exclude(category="").values_list("category", flat=True).distinct()
    return render(request, "blog/post_list.html", {
        "posts": page_obj.object_list,
        "page_obj": page_obj,
        "query": "",
        "selected_category": "",
        "categories": categories,
        "tags": tags,
        "selected_tag": tag,
    })


def post_detail(request, slug):
    post = get_object_or_404(
        _published_posts(), slug=slug
    )
    ctype = ContentType.objects.get_for_model(post)
    comment_settings = CommentSettings.objects.get(slug="default-config")
    comment_queryset = Comment.objects.filter(
        content_type=ctype, object_id=post.pk, parent__isnull=True, status="a"
    ).select_related("user").prefetch_related("children__user", "reactions__react")
    page_size = comment_settings.per_page or max(comment_queryset.count(), 1)
    comment_page = Paginator(comment_queryset, page_size).get_page(request.GET.get("comment_page"))
    rating_stats = BlogPostRating.objects.filter(post=post).aggregate(
        average=Avg("score"), count=Count("id")
    )
    user_rating = None
    if isinstance(request.user, Customer):
        user_rating = BlogPostRating.objects.filter(post=post, user=request.user).values_list("score", flat=True).first()
    related = _published_posts().exclude(pk=post.pk)
    if post.tags.exists():
        related = related.filter(tags__in=post.tags.all()).distinct()
    elif post.category:
        related = related.filter(category=post.category)
    return render(request, "blog/post_detail.html", {
        "post": post,
        "comments": comment_page.object_list,
        "comment_page": comment_page,
        "comment_settings": comment_settings,
        "related_posts": related[:3],
        "rating_average": rating_stats["average"] or 0,
        "rating_count": rating_stats["count"] or 0,
        "user_rating": user_rating,
    })


@login_required
def rate_post(request, slug):
    if request.method != "POST":
        return redirect("blog:post_detail", slug=slug)
    post = get_object_or_404(_published_posts(), slug=slug)
    if not isinstance(request.user, Customer):
        messages.error(request, "برای امتیازدهی باید با حساب مشتری وارد شوید.")
        return redirect("blog:post_detail", slug=slug)
    try:
        score = int(request.POST.get("score", ""))
    except (TypeError, ValueError):
        score = 0
    if score not in range(1, 6):
        messages.error(request, "امتیاز باید بین ۱ تا ۵ باشد.")
        return redirect("blog:post_detail", slug=slug)
    BlogPostRating.objects.update_or_create(
        post=post, user=request.user, defaults={"score": score}
    )
    messages.success(request, "امتیاز شما ثبت شد.")
    return redirect("blog:post_detail", slug=slug)


def _back_to_post(slug):
    return redirect("blog:post_detail", slug=slug)


@login_required
def create_comment(request, slug):
    post = get_object_or_404(_published_posts(), slug=slug)
    if request.method != "POST":
        return _back_to_post(slug)
    if not isinstance(request.user, Customer):
        messages.error(request, "برای ثبت دیدگاه باید با حساب مشتری وارد شوید.")
        return _back_to_post(slug)
    content = request.POST.get("content", "").strip()
    parent_id = request.POST.get("parent_id", "").strip()
    if not content or len(content) > 5000:
        messages.error(request, "متن دیدگاه باید بین ۱ تا ۵۰۰۰ نویسه باشد.")
        return _back_to_post(slug)
    comment = Comment(
        user=request.user, content_main=content, content=content,
        content_type=ContentType.objects.get_for_model(post), object_id=post.pk,
        is_spoiler=request.POST.get("is_spoiler") == "on", status="d"
    )
    if parent_id:
        comment.parent = get_object_or_404(
            Comment, pk=parent_id, content_type=comment.content_type,
            object_id=post.pk, parent__isnull=True, status="a"
        )
    comment.save()
    messages.success(request, "دیدگاه شما برای بررسی مدیر ارسال شد.")
    return _back_to_post(slug)


@login_required
def edit_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if comment.user_id != request.user.pk:
        return redirect("blog:post_list")
    post = comment.content_object
    if not isinstance(post, BlogPost):
        return redirect("blog:post_list")
    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content and len(content) <= 5000:
            comment.content = content
            comment.is_spoiler = request.POST.get("is_spoiler") == "on"
            comment.status_edited = "d"
            comment.save(update_fields=["content", "is_spoiler", "status_edited", "updated"])
            messages.success(request, "ویرایش دیدگاه برای تأیید مدیر ارسال شد.")
            return _back_to_post(post.slug)
        messages.error(request, "متن دیدگاه معتبر نیست.")
    return render(request, "comment/edit.html", {"comment": comment, "post": post})


@login_required
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if comment.user_id != request.user.pk:
        return redirect("blog:post_list")
    post = comment.content_object
    if request.method == "POST":
        comment.delete()
        messages.success(request, "دیدگاه حذف شد.")
        if isinstance(post, BlogPost):
            return _back_to_post(post.slug)
    return redirect("blog:post_list")


@login_required
def react_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk, status="a")
    post = comment.content_object
    if request.method == "POST" and isinstance(request.user, Customer):
        react = get_object_or_404(React, slug=request.POST.get("react_slug", "like"))
        reaction = Reaction.objects.filter(user=request.user, comment=comment).first()
        if reaction and reaction.react_id == react.pk:
            reaction.delete()
        elif reaction:
            reaction.react = react
            reaction.save(update_fields=["react"])
        else:
            Reaction.objects.create(user=request.user, comment=comment, react=react)
    if isinstance(post, BlogPost):
        return _back_to_post(post.slug)
    return redirect("blog:post_list")
