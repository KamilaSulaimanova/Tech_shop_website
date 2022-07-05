from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from shop.models import Wishlist
from website.settings import MEDIA_ROOT, MEDIA_URL
from shop.views import IndexView, ItemDetailView, ItemListView, WishtListView, test, create_review, add_to_cart, remove_from_cart, \
CartListView, plus_quantity, minus_quantity, add_to_wishlist, WishtListView, OrderView, make_order

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', IndexView.as_view(), name='index'),
    path('<int:pk>/', ItemDetailView.as_view(), name='detail'),
    path('store/', ItemListView.as_view(), name='item_list'),
    path('cart/', CartListView.as_view(), name='cart'),
    path('wishlist/', WishtListView.as_view(), name='wishlist'),
    path('order/', OrderView.as_view(), name='order'),


    path('create_review/<int:id>/', create_review, name='create_review'),
    path('add_to_cart/<int:pk>/', add_to_cart, name='add_to_cart'),
    path('add_to_wishlist/<int:pk>/', add_to_wishlist, name='add_to_wishlist'),
    path('remove_from_cart/<int:id>/', remove_from_cart, name='remove_from_cart'),
    path('plus_quantity/<int:id>/', plus_quantity, name='plus_quantity'),
    path('minus_quantity/<int:id>/', minus_quantity, name='minus_quantity'),
    path('make_order/', make_order, name='make_order'),
    # path('search/', search, name='search'),

    path('test/', test, name='test')
] + static(MEDIA_URL, document_root=MEDIA_ROOT)
