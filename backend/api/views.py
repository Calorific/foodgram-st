from django.shortcuts import get_object_or_404
from rest_framework import (
    viewsets,
    permissions,
    filters as drf_filters,
    status
)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    Ingredient,
    Recipe,
    Tag,
    RecipeIngredient,
    User,
    Follow,
)
from .serializers import (
    IngredientSerializer,
    RecipeSerializer,
    TagSerializer,
    ShortRecipeSerializer,
    RecipesUserSerializer,
    AvatarSerializer,
)
from .filters import RecipeFilter, IngredientFilter
from django.http import HttpResponse
from django.db.models import Sum
from djoser.views import UserViewSet
from .permissions import DefaultPermission


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.all()
    filterset_class = IngredientFilter
    filter_backends = [DjangoFilterBackend]
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    queryset = Recipe.objects.all()
    permission_classes = [DefaultPermission]
    filterset_class = RecipeFilter
    filter_backends = (
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    )
    search_fields = ("name", "text")
    ordering_fields = ("name", "pub_date")

    def _post_favorite(self, recipe, user):
        if recipe.favorited_by.filter(id=user.id).exists():
            return Response(
                {"errors": "Рецепт уже в избранном"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipe.favorited_by.add(user)
        serializer = ShortRecipeSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _delete_favorite(self, recipe, user):
        if not recipe.favorited_by.filter(id=user.id).exists():
            return Response(
                {"errors": "Рецепта нет в избранном"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipe.favorited_by.remove(user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == "POST":
            return self._post_favorite(recipe, user)

        return self._delete_favorite(recipe, user)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user
        is_in_cart = recipe.in_shopping_cart_for_users.filter(
            id=user.id
        ).exists()

        if request.method == "POST":
            if is_in_cart:
                return Response(
                    {"errors": "Рецепт уже добавлен в корзину"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            recipe.in_shopping_cart_for_users.add(user)
            serializer = ShortRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not is_in_cart:
            return Response(
                {"errors": "Рецепт еще не был добавлен в корзину"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipe.in_shopping_cart_for_users.remove(user)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        user = request.user
        items = (
            RecipeIngredient.objects.filter(
                recipe__in_shopping_cart_for_users=user
            )
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
            .order_by("ingredient__name")
        )

        if not items:
            return Response(
                {"detail": "В список ничего не добавлено"},
                status=status.HTTP_404_NOT_FOUND
            )

        result = ["Список покупок:"]
        for item in items:
            result.append(f"{item['ingredient__name']} - "
                          f"{item['ingredient__measurement_unit']}"
                          f"{item['total_amount']}")

        response_content = "\n".join(result)
        response = HttpResponse(
            response_content,
            content_type="text/plain; charset=utf-8",
            headers={
                'Content-Disposition': 'attachment; filename="список.txt"'
            },
        )

        return response

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[permissions.AllowAny],
        url_path="get-link",
        url_name="recipe-get-link",
    )
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        short_link = request.build_absolute_uri(
            f"/s/{recipe.id}/"
        )
        return Response(
            {"short-link": short_link},
            status=status.HTTP_200_OK
        )


class CustomUserViewSet(UserViewSet):
    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated]
    )
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(following__user=user)
        page = self.paginate_queryset(queryset)

        serializer = RecipesUserSerializer(
            page if page is not None else queryset,
            many=True,
            context={"request": request}
        )

        return (Response(serializer.data) if page is None
                else self.get_paginated_response(serializer.data))

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, id=id)

        if user == author:
            return Response(
                {"errors": "Нельзя подписываться на свой аккаунт"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        subscription = Follow.objects.filter(user=user, author=author)
        is_subscribed = subscription.exists()

        if request.method == "POST":
            if is_subscribed:
                return Response(
                    {"errors": "Подписка уже существует"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Follow.objects.create(user=user, author=author)
            serializer = RecipesUserSerializer(
                author,
                context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not is_subscribed:
            return Response(
                {"errors": "Вы еще не были подписаны"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _update_avatar(self, request):
        serializer = AvatarSerializer(request.user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def _delete_avatar(self, user):
        if user.avatar:
            user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["put", "delete"],
        permission_classes=[permissions.IsAuthenticated],
        url_path="me/avatar",
        url_name="user-me-avatar",
    )
    def avatar(self, request):
        if request.method == "PUT":
            return self._update_avatar(request)

        return self._delete_avatar(request.user)

    def get_permissions(self):
        self.permission_classes = ([permissions.AllowAny]
                                   if self.action in ["list", "retrieve"]
                                   else [permissions.IsAuthenticated])

        return super().get_permissions()
