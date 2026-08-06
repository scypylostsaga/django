from django.contrib import messages
from django.db.utils import OperationalError, ProgrammingError
from django.shortcuts import redirect, render

from api.models import Task


def home(request):
    """Render the home page with a task list and a create form."""
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        if title:
            Task.objects.create(title=title, description=description)
            messages.success(request, "Task added.")
        else:
            messages.error(request, "Title is required.")
        return redirect("home")

    tasks = []
    db_ready = True
    try:
        tasks = list(Task.objects.all())
    except (OperationalError, ProgrammingError):
        # Migrations have not been applied yet.
        db_ready = False

    context = {
        "tasks": tasks,
        "db_ready": db_ready,
        "completed_count": sum(1 for t in tasks if t.completed),
        "total_count": len(tasks),
    }
    return render(request, "core/home.html", context)


def toggle_task(request, task_id):
    """Toggle a task's completed state."""
    if request.method == "POST":
        try:
            task = Task.objects.get(pk=task_id)
            task.completed = not task.completed
            task.save(update_fields=["completed", "updated_at"])
        except Task.DoesNotExist:
            messages.error(request, "Task not found.")
    return redirect("home")


def delete_task(request, task_id):
    """Delete a task."""
    if request.method == "POST":
        Task.objects.filter(pk=task_id).delete()
        messages.success(request, "Task deleted.")
    return redirect("home")
