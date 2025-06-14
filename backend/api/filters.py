import django_filters
from .models import (
    Recipe,
    Ingredient,
)


class RecipeFilter(django_filters.FilterSet):
    author = django_filters.NumberFilter(
        field_name="author__id"
    )

    is_in_shopping_cart = django_filters.NumberFilter(
        method="filter_in_cart"
    )

    is_favorited = django_filters.NumberFilter(
        method="filter_is_favorited"
    )

    class Meta:
        model = Recipe
        fields = ["author", "is_favorited", "is_in_shopping_cart"]

    def filter_in_cart(self, queryset, _, value):
        user = self.request.user
        has_auth = user and user.is_authenticated
        print(has_auth, value, '===============')
        if has_auth:
            return (queryset.filter(in_shopping_cart_for_users=user) if value
                    else queryset.exclude(in_shopping_cart_for_users=user))
        else:
            return queryset.none() if value else queryset

    def filter_is_favorited(self, queryset, _, value):
        user = self.request.user
        has_auth = user and user.is_authenticated

        if has_auth:
            return (queryset.filter(favorited_by=user) if value
                    else queryset.exclude(favorited_by=user))
        else:
            return queryset.none() if value else queryset


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ['name']
