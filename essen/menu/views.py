# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404
from django.views import generic
from datetime import datetime, timedelta
import sys
from recipes.models import Recipe, Ingredient
from menu.models import Menu, Meal, LatePlate, AutoLatePlate, MealRating
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.encoding import python_2_unicode_compatible
from datetime import datetime, timedelta

# Create your views here.


def index(request, date='None'):
    template_name = 'menu/index.html'
    context_object_name = 'menu'

    if datetime.utcnow().today().weekday() < 6:
        days_from_sunday = 1 + datetime.utcnow().today().weekday()
    else:
        days_from_sunday = 0
    target_date = datetime.utcnow() - timedelta(days=days_from_sunday)
    y, m, d = target_date.year, target_date.month, target_date.day
    menu = Menu.objects.filter(start_date__year=y,
                                start_date__month=m,
                                start_date__day=d).first()
    date = date.encode('utf-8')
    if date != 'None':
        target_date = datetime.strptime(date, '%m/%d/%Y')
        y, m, d = target_date.year, target_date.month, target_date.day
        menu = Menu.objects.filter(start_date__year=y,
                                   start_date__month=m,
                                   start_date__day=d).first()


    return render(request, template_name, {context_object_name: menu, 'target_date': target_date})

def add_menu(request):
    template_name = "menu/add_menu.html"
    context_object_name = 'recipe_choices'

    recipe_choices = Recipe.objects.all()

    return render(request, template_name, {context_object_name: recipe_choices, 'steward': check_if_steward(request.user)})


def submit_menu(request):
    if not (request.user.is_authenticated and check_if_steward(request.user)):
        return HttpResponseRedirect(reverse('menu:index'))

    days_to_num = {"Sunday Brunch": 0, "Sunday Dinner": 0, "Monday Dinner": 1, "Tuesday Dinner": 2,
                   "Wednesday Dinner": 3, "Thursday Dinner": 4}

    d = dict(request.POST.iterlists())
    start_date = datetime.strptime(request.POST.get('start_date'), "%Y-%m-%d").date()

    Menu.objects.filter(start_date=start_date).delete()

    menu = Menu(start_date = start_date,
                servings = request.POST.get("serving_size"),
                notes = request.POST.get("notes"))
    menu.save()


    for key, item in d.items():
        if "day" in key:
            day_num = key.split("_")[1]
            meal_key = "item_" + day_num

            recipes = d[meal_key] #list of all recipe names corresponding to that meal in the menu
            meal = Meal(menu=menu,
                        date=start_date+timedelta(days_to_num[request.POST.get(key)]),
                        meal_name=request.POST.get(key))
            meal.save()

            # add automatic lateplates
            for auto_plate in AutoLatePlate.objects.all():
                if str(request.POST.get(key)) in str(auto_plate.days):
                    l = LatePlate(meal=meal, name=auto_plate.username)
                    l.save()

            # add recipes
            for r in recipes:
                recipe = Recipe.objects.filter(recipe_name=r).first()
                meal.recipes.add(recipe)

    return HttpResponseRedirect(reverse('menu:index'))

class DetailView(generic.DetailView):
    model = Meal
    template_name = "menu/rate_meal.html"

def view_meal(request, pk):
    template_name = 'menu/display_meal.html'
    context_object_name = 'info'

    meal = get_object_or_404(Meal, pk=pk)

    info = {"meal" : meal, "users" : [u.get_full_name for u in User.objects.all()]}

    return render(request, template_name, {context_object_name: info})


def add_lateplate(request, meal_pk, user_pk):
    meal = get_object_or_404(Meal, pk=meal_pk)
    user = get_object_or_404(User, pk=user_pk)

    if user.is_authenticated:
        l = LatePlate(name=request.POST.get("name"), meal=meal)
        l.save()

    return HttpResponseRedirect(reverse('menu:display_meal', args=[meal_pk]))


def remove_lateplate(request, lateplate_pk, user_pk):
    lateplate = get_object_or_404(LatePlate, pk=lateplate_pk)

    if request.user.is_authenticated:
        meal_id = lateplate.meal.id
        lateplate.delete()

    return HttpResponseRedirect(reverse('menu:display_meal', args=[meal_id]))


def auto_lateplates(request):
    template_name = 'menu/auto_lateplates.html'
    map = {"Sunday Brunch": 0, "Sunday Dinner": 1, "Monday Dinner": 2, "Tuesday Dinner": 3,
                   "Wednesday Dinner": 4, "Thursday Dinner": 5}
    requested_days = [{"day": "Sunday Brunch", "state": False}, {"day": "Sunday Dinner", "state": False}, {"day": "Monday Dinner", "state": False},
                      {"day": "Tuesday Dinner", "state": False},  {"day": "Wednesday Dinner", "state": False}, {"day": "Thursday Dinner", "state": False},]

    lateplate = AutoLatePlate.objects.filter(username=request.user.username).first()

    if lateplate != None:
        print(lateplate.days)
        for day in lateplate.days.split(";"):
            print("day, " ,day)
            requested_days[map[day]] = {"day": day, "state": True}

    return render(request, template_name, {"days" : requested_days})

def submit_auto_lateplates(request):
    if request.user.is_authenticated:
        d = dict(request.POST.iterlists())
        # delete the previous lateplate registrys
        AutoLatePlate.objects.filter(username=request.user.username).delete()
        print(d)
        # add the new one
        if "date" in d.keys():
            days = ""
            for day in d.get("date"):
                if days != "":
                    days += ";"
                days += day
                print(day)
            auto = AutoLatePlate(username=request.user.username, days=days)
            auto.save()

    return HttpResponseRedirect(reverse('menu:index'))


def shopper(request, pk):
    template_name = 'menu/shopper.html'
    context_object_name = 'ingredients'
    map = {"Sunday Brunch": 0, "Sunday Dinner": 1, "Monday Dinner": 2, "Tuesday Dinner": 3,
                   "Wednesday Dinner": 4, "Thursday Dinner": 5}

    menu = get_object_or_404(Menu, pk=pk)
    d = dict(request.GET.iterlists())

    after_filter = False
    after_date = (datetime.now() - timedelta(days=8)).date()
    if "filter_date" in d:
        after_date = map[d["after"][0]]
        after_filter = d["filter_date"][0]
    else:
        after_date = -1 # accept all recipes for shopping list

    all_ingredients = {}

    for meal in menu.meal_set.all():
        if map[meal.meal_name] > after_date:
            for recipe in meal.recipes.all():
                scale_factor = float(menu.servings)/recipe.serving_size
                for ingredient in recipe.ingredient_set.all():
                    ing_type = (ingredient.ingredient_name.lower(), ingredient.units.lower())
                    if ing_type not in all_ingredients:
                        all_ingredients[ing_type] = float(ingredient.quantity) * scale_factor
                    else:
                        all_ingredients[ing_type] += float(ingredient.quantity) * scale_factor

    ing_list = [{"ing": key[0], "quantity": value, "unit": key[1]} for key, value in all_ingredients.items()]
    ing_list.sort(key=lambda x: x["ing"])

    return render(request, template_name, {context_object_name: ing_list, "filter_date": after_filter,
                                           "after_date": d["after"][0], "notes":menu.notes})


def ingredient_info(request, ing, menu):
    template_name = 'menu/ingredient_info.html'
    context_object_name = 'usages'

    search = get_object_or_404(Ingredient, pk=str(ing))
    menu = get_object_or_404(Menu, pk=str(menu))

    ingredient_uses = []

    for meal in menu.meal_set.all():
        for recipe in meal.recipes.all():
            scale_factor = menu.servings/recipe.serving_size
            for ingredient in recipe.ingredient_set.all():

                if ingredient.ingredient_name == search.ingredient_name and meal.date > datetime.now().date():
                    ingredient_uses.append(str(ingredient.quantity * scale_factor) + " " + ingredient.units + " for " + meal.meal_name)

    return render(request, template_name, {context_object_name: ingredient_uses})


def submit_rating(request, pk):
    if request.user.is_authenticated:
        d = dict(request.GET.iterlists())
        meal = get_object_or_404(Meal, pk=pk)

        print("rating", d)
        # rating = d[]

        if 'rate' in d:
            previous_rating = MealRating.objects.filter(username=request.user.username).filter(meal=meal)
            previous_rating.delete()

            rating = MealRating(meal=meal, username=request.user.username, rating=d['rate'][0], comment=d['comment-box'][0])
            rating.save()

        # MealRating(meal=meal, username=request.user.username, rating=)

    return HttpResponseRedirect(reverse('menu:index'))


def see_reviews(request):
    final_list = []
    steward = False
    if request.user.is_authenticated and check_if_steward(request.user):
        steward = True
        d = {}
        for review in MealRating.objects.all():
            if review.meal in d:
                d[review.meal].append((review.rating, review.comment, review.username))
            else:
                d[review.meal] = [(review.rating, review.comment, review.username)]

        print(d)

        final_list = []
        for key, item in d.items():
            overall_rating = float(sum([x[0] for x in item]))/len(item)
            comment_list = []
            for entry in item:
                comment_list.append({"username":entry[2], "comment":entry[1], "rating":entry[0]})
            final_list.append({"meal":key, "overall_rating":overall_rating, "comments":comment_list})
        final_list.sort(key=lambda entry: entry["meal"].date, reverse=True)

    return render(request, template_name="menu/menu_reviews.html", context={"all_meals": final_list, "steward":steward})

def check_if_steward(user):
    return user.groups.all().filter(name="stewards").count() > 0