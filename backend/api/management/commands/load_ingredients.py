import json
from django.core.management.base import BaseCommand
from api.models import Ingredient


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            Ingredient.objects.all().delete()
        except Exception as e:
            print(e)
            return

        file_path = 'ingredients.json'
        try:
            file = open(file_path, 'r', encoding='utf-8')
            ingredients_data = json.load(file)
        except Exception as e:
            print(e)
            return

        new_ingredients = []
        for item in ingredients_data:
            new_ingredients.append(
                Ingredient(
                    name=item.get('measurement_unit'),
                    measurement_unit=item.get('measurement_unit')
                )
            )

        try:
            Ingredient.objects.bulk_create(
                new_ingredients,
                ignore_conflicts=True
            )
        except Exception as e:
            print(e)
