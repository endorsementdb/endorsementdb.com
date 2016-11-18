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

from election import views


urlpatterns = [
    url(r'^$', views.browse, name='browse'),
    url(r'^admin/', admin.site.urls),
    url(r'^api/endorsements.json', views.get_endorsements,
        name='get-endorsements'),
    url(r'^api/tags.json', views.get_tags, name='get_tags'),
    url(r'^api/search.json', views.search_endorsers,
        name='search_endorsers'),
    url(r'^endorser/$', views.add_endorser,
        name='add-endorser'),
    url(r'^endorser/(?P<pk>\d+)/$', views.view_endorser,
        name='view-endorser'),
    url(r'^endorser/(?P<pk>\d+)/add-account$',
        views.add_account, name='add-account'),
    url(r'^endorser/(?P<pk>\d+)/add-endorsement$',
        views.add_endorsement, name='add-endorsement'),
    url(r'^endorsers/random$',
        views.random_endorser, name='random-endorser'),
    url(r'^progress/wikipedia$',
        views.progress_wikipedia, name='progress-wikipedia'),
    url(r'^progress/wikipedia/(?P<slug>[^/]+)/missing$',
        views.progress_wikipedia_missing, name='progress-wikipedia-missing'),
    url(r'^progress/wikipedia/(?P<slug>[^/]+)/(?P<mode>\w+)$',
        views.progress_wikipedia_list, name='progress-wikipedia-list'),
    url(r'^progress/tagging$', views.progress_tagging,
        name='progress-tagging'),
    url(r'^progress/twitter$', views.progress_twitter,
        name='progress-twitter'),
    url(r'^confirm/endorsements$',
        views.confirm_endorsements, name='confirm-endorsements'),
    url(r'^confirm/endorsements/(?P<pk>\d+)', views.confirm_endorsement,
        name='confirm-endorsement'),
    url(r'^confirm/newspapers$', views.confirm_newspapers,
        name='confirm-newspapers'),
    url(r'^confirm/newspapers/(?P<pk>\d+)', views.confirm_newspaper,
        name='confirm-newspaper'),
    url(r'^stats/states$', views.stats_states, name='stats-states'),
    url(r'^stats/predictions$', views.stats_predictions,
        name='stats-predictions'),
    url(r'^stats/tags$', views.stats_tags, name='stats-tags'),
    url(r'^stats/charts$', views.charts, name='charts'),
]


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
