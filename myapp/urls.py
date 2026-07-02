
from django.urls import path
from myapp import views

urlpatterns = [
    path('addbook_get/', views.addbook_get),
    path('addbook_post/', views.addbook_post),
    path('view_books/', views.view_books),
    path("book-gallery/<int:book_id>/", views.book_gallery),
    path("edit-book/<int:book_id>/", views.edit_book),
    path('delete_book/<int:id>/', views.delete_book),
    path('dashboard/', views.dashboard),
    path('admin_login_get/', views.admin_login_get),
    path('admin_login_post/', views.admin_login_post),
    path('logout/', views.admin_logout),


    #user
    path('user_homepage/', views.user_homepage),
    path('user_view_book_details/<int:id>/', views.user_view_book_details),
    path('add_to_cart/<int:book_id>/', views.add_to_cart, name='add_to_cart'),
    path('view_cart/', views.view_cart, name='view_cart'),
    path('update_cart_item/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('remove_from_cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),

    path('add_to_wishlist/<int:id>/', views.add_to_wishlist),
    path('remove_wishlist/<int:id>/', views.remove_wishlist),
    path('view_wishlist/', views.view_wishlist),
    path('move_to_cart/<int:book_id>/', views.move_to_cart, name='move_to_cart'),

    path('razorpay-payment/', views.razorpay_payment, name='razorpay_payment'),
    path('razorpay-payment-success/', views.razorpay_payment_success, name='razorpay_payment_success'),
    path('send_order_confirmation_emails/', views.send_order_confirmation_emails, name='send_order_confirmation_emails'),

    path('checkout/', views.checkout, name='checkout'),
    path('place_order/', views.place_order, name='place_order'),
    path('order_confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('my_orders/', views.my_orders, name='my_orders'),


]
