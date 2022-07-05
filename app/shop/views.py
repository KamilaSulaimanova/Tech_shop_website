from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.views.generic import ListView, DetailView, TemplateView
from .models import Item, Category, Color, ColorItemQuantity, ItemImage, Brand, Review, Cart, Wishlist, Order
import telegram_send
from django.conf import settings
from django.core.mail import send_mail
from . import tasks



class IndexView(ListView):
    model = Item
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context


class ItemDetailView(DetailView):
    model = Item
    template_name = 'product.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['images'] = ItemImage.objects.filter(item=self.get_object())
        context['colors'] = ColorItemQuantity.objects.filter(item=self.get_object())
        context['related_items'] = Item.objects.filter(category=self.get_object().category)
        reviews = Review.objects.filter(item=self.get_object())
        context['reviews'] = reviews
        rating_list = []
        for rating in reviews.values_list('rating'):
            rating_list.append(rating[0])
        rating_dict = {}

        for i in range(1, 6):
            rating_dict[f'rating_{i}'] = rating_list.count(i)
        try:
            avg = round(sum(rating_list)/len(rating_list), 1)
        except ZeroDivisionError:
            avg = 0
        rating_dict['avg'] = avg
        rating_len = len(rating_list)
        rating_dict['rating_len'] = rating_len
        context['rating_dict'] = rating_dict
        return context


class ItemListView(ListView):
    model = Item
    template_name = 'store.html'
    paginate_by = 2


    def get_queryset(self):
        queryset = self.model.objects.all()
        price_min = self.request.GET.get('price-min')
        price_max = self.request.GET.get('price-max')
        category = self.request.GET.get('category')
        search = self.request.GET.get('search')
        if category:
            if category != '0':
                queryset = queryset.filter(category_id=category)
            if search:
                queryset = queryset.filter(name__icontains=search)
        
        if price_min and price_max:
            queryset = queryset.filter(price__gt = price_min, price__lte = price_max)

            category_ids = []
            brand_ids = []
            for name in self.request.GET.keys():
                if name.startswith('category'):
                    category_ids.append(int(name.split('-')[1]))
                elif name.startswith('brand'):
                    brand_ids.append(int(name.split('-')[1]))
            if category_ids:
                queryset = queryset.filter(category__in=category_ids)
            if brand_ids:
                queryset = queryset.filter(brand__in=brand_ids)
        return queryset


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['brands'] = Brand.objects.all()
        return context 


class CartListView(ListView):
    model = Cart
    template_name = 'cart.html'


class WishtListView(ListView):
    model = Wishlist
    template_name = 'wishlist.html'


class OrderView(TemplateView):
    template_name = 'checkout.html'


def make_order(request):
    name = request.POST.get('name')
    email = request.POST.get('email')
    address = request.POST.get('address')
    phone_number = request.POST.get('tel')
    notes = request.POST.get('notes')

    order_address = f'Order from {name}, email: {email}, to address: {address}, telephone number: {phone_number}'
    messages = [order_address,]

    carts = Cart.objects.filter(session_key=request.session.session_key, ordered=False)
    for cart in carts:
        if cart.quantity != 0:
            new_order = Order(name=name, email=email, address=address, phone_number=phone_number, notes=notes, cart=cart)
            cart.item.quantity -= cart.quantity
            cart.item.save()
            new_order.save()
            cart.ordered = True
            cart.save()
            messages.append(f'Product: {cart.item.item.name}, quantity: {cart.quantity}, price: {cart.get_price()}, with total price: {cart.get_final_price()}')
    
    if messages:
        messages.insert(0, f'Order from {name}, email: {email}, to address: {address}, telephone number: {phone_number}')
        tasks.send_massive_telegram.delay(messages)
    # send_mail('Your order', f'Order from {name}, to address: {address}, telephone number: {phone_number}', settings.EMAIL_HOST_USER, [email])
    return HttpResponseRedirect(reverse('index'))




def create_review(request, id):
    if request.method == "POST":
        item = Item.objects.get(id=id)
        name = request.POST.get('name')
        email = request.POST.get('email')
        text = request.POST.get('text')
        rating = request.POST.get('rating')

        new_review = Review(name=name, email=email, text=text, rating=int(rating), item=item)
        new_review.save()

        return redirect('detail', pk=id)


def add_to_cart(request, pk):
    main_item = get_object_or_404(Item, pk=pk)
    color_id = request.GET.get('color')
    quantity = request.GET.get('quantity') if request.GET.get('quantity') else 1
    session_key = request.session.session_key
    if color_id:
        item = get_object_or_404(ColorItemQuantity, id=color_id)
    else:
        item = ColorItemQuantity.objects.filter(item=main_item, quantity__gt=0)[0]
    try:
        cart = Cart.objects.get(session_key=request.session.session_key, ordered=False, item=item)
    except ObjectDoesNotExist as e:
        cart = Cart(item=item, quantity=quantity, session_key=session_key)
    else:
        cart.quantity += int(quantity)
        messages.add_message(request, messages.SUCCESS, 'Product was successfully updated')
    finally:
        cart.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def add_to_wishlist(request, pk):
    main_item = get_object_or_404(Item, pk=pk)
    color_id = request.GET.get('color')
    quantity = request.GET.get('quantity') if request.GET.get('quantity') else 1
    session_key = request.session.session_key
    if color_id:
        item = get_object_or_404(ColorItemQuantity, id=color_id)
    else:
        item = ColorItemQuantity.objects.filter(item=main_item, quantity__gt=0)[0]

    Wishlist.objects.create(item=item, quantity=quantity, session_key=session_key)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def remove_from_cart(request, id):
    cart = get_object_or_404(Cart, id=id)
    cart.delete()
    messages.add_message(request, messages.WARNING, 'Product was successfully deleted from the cart')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

def test(request):
    print(request.GET)
    return HttpResponse('Ok')


def plus_quantity(request, id):
    cart_item = get_object_or_404(Cart, id=id)
    cart_item.quantity += 1
    cart_item.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def minus_quantity(request, id):
    cart_item = get_object_or_404(Cart, id=id)
    cart_item.quantity -= 1
    cart_item.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# def search(request):
#     category = request.GET.get('category', None)
#     search = request.GET.get('search', None)
#     if category:
#         results = Item.objects.filter(category=category, name__icontains=search)
#     else:
#         results = Item.objects.filter(name__icontains=search)
#     context = {
#         'search': search,
#         'results': results,
#         'categories': category
#         }
#     return render(request, 'store.html', context)