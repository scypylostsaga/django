from rest_framework import viewsets

from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    """Full CRUD API for tasks."""

    queryset = Task.objects.all()
    serializer_class = TaskSerializer
