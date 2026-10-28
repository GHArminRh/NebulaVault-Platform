from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from accounts.models import Customer
from blog.models import BlogPost
from .models import Comment, CommentSettings, React, Reaction

def _post_for_comment(comment):
    obj=comment.content_object
    if not isinstance(obj,BlogPost): raise PermissionDenied
    return obj

@login_required
def create(request):
    slug=request.POST.get("slug","")
    post=get_object_or_404(BlogPost,slug=slug,status=BlogPost.Status.PUBLISHED,published_at__lte=timezone.now())
    if request.method!="POST": return redirect("blog:post_detail",slug=slug)
    if not isinstance(request.user,Customer): raise PermissionDenied
    content=request.POST.get("content","").strip()
    if not content or len(content)>5000:
        messages.error(request,"متن دیدگاه باید بین ۱ تا ۵۰۰۰ نویسه باشد.")
        return redirect("blog:post_detail",slug=slug)
    settings_obj=get_object_or_404(CommentSettings,slug="default-config")
    ctype=ContentType.objects.get_for_model(post)
    parent=None
    parent_id=request.POST.get("parent_id","").strip()
    if parent_id:
        parent=get_object_or_404(Comment,pk=parent_id,content_type=ctype,object_id=post.pk,parent__isnull=True,status="a")
        if not settings_obj.allow_reply: raise PermissionDenied
    Comment.objects.create(user=request.user,content_main=content,content=content,parent=parent,is_spoiler=request.POST.get("is_spoiler")=="on",status="d" if settings_obj.status_check else "a",content_type=ctype,object_id=post.pk)
    messages.success(request,"دیدگاه شما برای بررسی مدیر ارسال شد.")
    return redirect("blog:post_detail",slug=slug)

@login_required
def edit(request,pk):
    comment=get_object_or_404(Comment,pk=pk)
    if not isinstance(request.user,Customer) or comment.user_id!=request.user.pk: raise PermissionDenied
    post=_post_for_comment(comment)
    settings_obj=get_object_or_404(CommentSettings,slug="default-config")
    if not settings_obj.allow_edit: raise PermissionDenied
    if request.method=="POST":
        content=request.POST.get("content","").strip()
        if content and len(content)<=5000:
            comment.content=content
            comment.is_spoiler=request.POST.get("is_spoiler")=="on"
            if settings_obj.status_edited_check and comment.content_main!=content: comment.status_edited="d"
            else: comment.status_edited="a"; comment.content_main=content
            comment.save()
            messages.success(request,"ویرایش دیدگاه برای بررسی مدیر ارسال شد.")
            return redirect("blog:post_detail",slug=post.slug)
        messages.error(request,"متن دیدگاه معتبر نیست.")
    return render(request,"comment/edit.html",{"comment":comment,"post":post})

@login_required
def delete(request,pk):
    comment=get_object_or_404(Comment,pk=pk)
    if comment.user_id!=request.user.pk: raise PermissionDenied
    post=_post_for_comment(comment)
    settings_obj=get_object_or_404(CommentSettings,slug="default-config")
    if not settings_obj.allow_delete: raise PermissionDenied
    if request.method=="POST":
        comment.delete()
        messages.success(request,"دیدگاه حذف شد.")
    return redirect("blog:post_detail",slug=post.slug)

@login_required
def react(request,pk):
    comment=get_object_or_404(Comment,pk=pk,status="a")
    post=_post_for_comment(comment)
    settings_obj=get_object_or_404(CommentSettings,slug="default-config")
    if not settings_obj.allow_reaction: raise PermissionDenied
    if request.method=="POST" and isinstance(request.user,Customer):
        react_obj=get_object_or_404(React,slug=request.POST.get("react_slug","like"))
        existing=Reaction.objects.filter(user=request.user,comment=comment).first()
        if existing and existing.react_id==react_obj.pk: existing.delete()
        elif existing: existing.react=react_obj; existing.save(update_fields=["react"])
        else: Reaction.objects.create(user=request.user,comment=comment,react=react_obj)
    return redirect("blog:post_detail",slug=post.slug)
