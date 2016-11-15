"""election URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin

import endorsements.views
import wikipedia.views


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', endorsements.views.index, name='index'),
    url(r'^api/endorsements.json', endorsements.views.get_endorsements,
        name='get-endorsements'),
    url(r'^api/tags.json', endorsements.views.get_tags, name='get_tags'),
    url(r'^api/search.json', endorsements.views.search_endorsers,
        name='search_endorsers'),
    url(r'^endorser/$', endorsements.views.add_endorser,
        name='add-endorser'),
    url(r'^endorser/(?P<pk>\d+)/$', endorsements.views.view_endorser,
        name='view-endorser'),
    url(r'^endorser/(?P<pk>\d+)/add-account$',
        endorsements.views.add_account, name='add-account'),
    url(r'^endorser/(?P<pk>\d+)/add-endorsement$',
        endorsements.views.add_endorsement, name='add-endorsement'),
    url(r'^endorsers/random$',
        endorsements.views.random_endorser, name='random-endorser'),
    url(r'^progress$',
        wikipedia.views.progress_index, name='progress-index'),
    url(r'^progress/(?P<slug>[^/]+)/missing$',
        wikipedia.views.progress_missing, name='progress-missing'),
    url(r'^progress/(?P<slug>[^/]+)/(?P<mode>\w+)$',
        wikipedia.views.progress_list, name='progress-list'),
    url(r'^confirm$',
        wikipedia.views.confirm_next, name='confirm-next'),
    url(r'^confirm/(?P<pk>\d+)',
        wikipedia.views.confirm_endorsement, name='confirm-endorsement'),
    url(r'^newspaper$',
        wikipedia.views.newspaper_next, name='newspaper-next'),
    url(r'^newspaper/(?P<pk>\d+)',
        wikipedia.views.newspaper_add, name='newspaper-add'),
    url(r'^charts$',
        endorsements.views.charts, name='charts'),
    url(r'^results$', wikipedia.views.results, name='results'),
]


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
