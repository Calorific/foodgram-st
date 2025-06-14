from rest_framework import serializers
from django.db import transaction
from drf_extra_fields.fields import Base64ImageField
from .models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    User,
    MIN_INT_VALUE,
    MAX_INT_VALUE,
)
from django.core.validators import (
    MinValueValidator, MaxValueValidator,
)
from django.contrib.auth.validators import (
    UnicodeUsernameValidator,
)
from rest_framework.validators import (
    UniqueValidator,
)


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(
        required=True
    )

    class Meta:
        model = User
        fields = ("avatar",)


class UserCreateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        validators=[
            UnicodeUsernameValidator(),
            UniqueValidator(
                queryset=User.objects.all(),
                message="Пользователь с таким именем уже существует.",
            ),
        ],
        max_length=150,
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "password",
            "first_name",
            "last_name",
        )
        extra_kwargs = {
            "password": {"write_only": True},
            "id": {"read_only": True},
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(
        source="ingredient.id"
    )
    name = serializers.ReadOnlyField(
        source="ingredient.name"
    )
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "amount", "measurement_unit",)


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    avatar = serializers.ImageField(
        read_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "avatar",
            "is_subscribed",
        )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")

        if not request:
            return False

        user = request.user

        return (user and user.is_authenticated and isinstance(obj, User)
                and user.follower.filter(author=obj).exists())


class RecipeIngredientSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )
    amount = serializers.IntegerField(
        min_value=MIN_INT_VALUE,
        max_value=MAX_INT_VALUE
    )


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    image = Base64ImageField(required=True)
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    cooking_time = serializers.IntegerField(
        validators=[
            MinValueValidator(
                MIN_INT_VALUE,
                message=f"Минимальное значение {MIN_INT_VALUE}"
            ),
            MaxValueValidator(
                MAX_INT_VALUE,
                message=f"Минимальное значение {MAX_INT_VALUE}"
            )
        ],
        required=True,
    )
    ingredients = RecipeIngredientSerializer(
        many=True,
        write_only=True,
        source="ingredients_for_processing"
    )

    class Meta:
        model = Recipe
        fields = (
            "id",
            "name",
            "author",
            "cooking_time",
            "image",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "text",
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation.pop("ingredients_for_processing", None)

        representation["ingredients"] = RecipeIngredientReadSerializer(
            instance.recipe_ingredients.all(),
            many=True,
            context=self.context,
        ).data

        return representation

    def validate(self, data):
        image = data.get('image')
        if image is None:
            raise serializers.ValidationError(
                {"image": "Image обязательное поле"}
            )

        ingredients = data.get('ingredients_for_processing')
        if not ingredients:
            raise serializers.ValidationError(
                {"ingredients": "Ингридиенты не могут быть пустыми"}
            )

        ingredient_ids = []
        for item in ingredients:
            ingredient = item.get("id")
            if not isinstance(ingredient, Ingredient):
                raise serializers.ValidationError(
                    {"ingredients": "Неверный ID"}
                )
            ingredient_ids.append(ingredient.id)

        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                {"ingredients": "Ингредиенты должны быть уникальными"}
            )

        return data

    def get_is_in_shopping_cart(self, obj):
        user = self.context["request"].user

        if user and user.is_authenticated:
            return obj.in_shopping_cart_for_users.filter(id=user.id).exists()
        return False

    def get_is_favorited(self, obj):
        user = self.context["request"].user

        if user and user.is_authenticated:
            return obj.favorited_by.filter(id=user.id).exists()
        return False

    def _create_ingredients(self, recipe, ingredients_data):
        ingredients_to_create = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=item["id"],
                amount=item["amount"]
            )
            for item in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(ingredients_to_create)

    @transaction.atomic
    def create(self, validated_data):
        ingredients_data = validated_data.pop(
            "ingredients_for_processing"
        )

        validated_data["author"] = self.context["request"].user
        recipe = Recipe.objects.create(**validated_data)

        self._create_ingredients(recipe, ingredients_data)

        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop(
            "ingredients_for_processing",
            None
        )

        for field in ("name", "text", "cooking_time", "image"):
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        instance.save()

        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            self._create_ingredients(instance, ingredients_data)

        return instance


class ShortRecipeSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
        read_only_fields = fields


class RecipesUserSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(
        read_only=True,
        required=False,
        allow_null=True
    )
    recipes = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "recipes",
            "recipes_count",
            "avatar",
        )
        read_only_fields = fields

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        return (request and request.user.is_authenticated
                and request.user.follower.filter(author=obj).exists())

    def get_recipes(self, obj):
        request = self.context.get("request")
        queryset = obj.recipes.all()

        if request:
            recipes_limit = request.query_params.get("recipes_limit")

            if recipes_limit:
                try:
                    recipes_limit = int(recipes_limit)
                    if recipes_limit > 0:
                        queryset = queryset[:recipes_limit]
                except ValueError as e:
                    print(e)
                    pass
        return ShortRecipeSerializer(
            queryset,
            many=True,
            context=self.context
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()
