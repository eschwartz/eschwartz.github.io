---
layout: post
tags : [javascript, node, node.js, cache, crisp-cache, lru cache]
title: "Is Your Cache Crispy Fresh?"
---
For my day job, I work at a company called [Aeris Weather](http://www.aerisweather.com). Among other things, our company sells weather data services via [a pretty robust data API](http://www.aerisweather.com/support/docs/api/reference/endpoints/), and [a map tile server](http://www.aerisweather.com/support/docs/aeris-overlays/).

I just finished writing up [a post for the company blog](http://www.aerisweather.com/blog/is-your-cache-crispy-fresh/) about how we came to roll our own caching library:

> There are several [great](https://github.com/isaacs/node-lru-cache) [caching](https://github.com/addisonj/node-cacher) [libraries](https://github.com/ptarjan/node-cache) out there, but we had trouble finding something that matched all of our requirements:

> * Can cache any type of resource (ie, not just an http cache)
* Can serve “stale” data, while pre-fetching fresh data for the next request
* Can control memory usage with configurable limits
* Provides a clean separation between business logic and the cache layer
* Locks cache misses, so we don’t have to worry about [cache-stampeding](https://en.wikipedia.org/wiki/Cache_stampede) when a resource expires.

> Nothing we found quite fit that bill, so my colleague [Seth Miller](http://four43.com/) decided to roll his own instead called [CrispCache](https://github.com/four43/node-crisp-cache).

[Check it out](http://www.aerisweather.com/blog/is-your-cache-crispy-fresh/), let me know what you think!

## [Aeris Weather Blog: Is Your Cache Crispy Fresh?](http://www.aerisweather.com/blog/is-your-cache-crispy-fresh/)