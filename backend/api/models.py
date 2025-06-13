from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.validators import MinValueValidator
from django.db import models

MAX_EMAIL_LENGTH = 254
MAX_LENGTH = 150


class User(AbstractUser):
    email = models.EmailField(
        verbose_name="Email",
        max_length=MAX_EMAIL_LENGTH,
        unique=True
    )
    username = models.CharField(
        verbose_name="Username",
        max_length=MAX_LENGTH,
        unique=True,
    )
    first_name = models.CharField(
        verbose_name="Имя",
        max_length=MAX_LENGTH
    )
    last_name = models.CharField(
        verbose_name="Фамилия",
        max_length=MAX_LENGTH
    )
    avatar = models.ImageField(
        verbose_name="Аватар", upload_to="users/avatars/",
        null=True, blank=True
    )

    groups = models.ManyToManyField(
        Group,
        verbose_name="Группы",
        blank=True,
        related_name="api_user_groups",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name="Права",
        blank=True,
        related_name="api_user_permissions",
        related_query_name="user",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["username"]


class Follow(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Подписчик",
        on_delete=models.CASCADE,
        related_name="follower",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Автор, на которого подписаны",
        on_delete=models.CASCADE,
        related_name="following",
    )
    created_at = models.DateTimeField(
        verbose_name="Дата подписки",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                name="unique_follow",
                fields=["user", "author"],
            ),
            models.CheckConstraint(
                name="prevent_self_follow",
                check=~models.Q(user=models.F("author")),
            ),
        ]


class Ingredient(models.Model):
    name = models.CharField(
        verbose_name="Название",
        max_length=128
    )
    measurement_unit = models.CharField(
        verbose_name="Ед. измерения",
        max_length=64
    )

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["name", "measurement_unit"],
                name="unique_ingredient_measure"
            )
        ]


class Tag(models.Model):
    name = models.CharField(
        verbose_name="Название",
        max_length=50,
        unique=True
    )
    color = models.CharField(
        verbose_name="Цвет (HEX)",
        max_length=7,
        unique=True,
        validators=[],
    )
    slug = models.SlugField(
        verbose_name="Slug",
        max_length=50,
        unique=True
    )

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        ordering = ("name",)


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        verbose_name="Автор",
        on_delete=models.CASCADE,
        related_name="recipes",
    )
    name = models.CharField(
        verbose_name="Название",
        max_length=128
    )
    image = models.ImageField(
        verbose_name="Изображение",
        upload_to="recipes/images/",
    )
    text = models.TextField(
        verbose_name="Описание"
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name="Ингредиенты",
        related_name="recipes",
        through="RecipeIngredient",
    )
    tags = models.ManyToManyField(
        Tag,
        related_name="recipes",
        verbose_name="Теги",
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name="Время приготовления, мин.",
        validators=[],
    )
    pub_date = models.DateTimeField(
        verbose_name="Дата публикации",
        auto_now_add=True
    )
    favorited_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="favorite_recipes",
        verbose_name="В избранном у",
        blank=True,
    )
    in_shopping_cart_for_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="shopping_cart_recipes",
        verbose_name="В списке покупок у",
        blank=True,
    )

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"
        ordering = ["-pub_date"]


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
        verbose_name="Рецепт",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.PROTECT,
        related_name="ingredient_recipes",
        verbose_name="Ингредиент",
    )
    amount = models.PositiveIntegerField(
        verbose_name="Количество",
        validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = "Ингредиент в рецепте"
        verbose_name_plural = "Ингредиенты в рецепте"
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "ingredient"],
                name="unique_recipe_ingredient"
            )
        ]
