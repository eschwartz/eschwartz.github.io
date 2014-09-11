---
layout: post
tags : [javascript, Wire.js, Almond.js, RequireJS, IoC, dependency injection]
title: "Optimize Wire.js builds with an AMD shim"
---
I'm a total nerd over dependency injection, so I've really enjoyed using [Wire.js](https://github.com/cujojs/wire). If you're not familiar with Wire.js, it's basically a dependency injection library for javascript.


I'm using Wire.js on a weather mapping application called [Aeris Interactive](http://wx.hamweather.com/local/us/mn/minneapolis/interactive.html), which I am building my for my employer, [HAMWeather](http://www.hamweather.com/). The heavy lifting for Aeris Interactive is all done by an open source library I built for HAMWeather called [Aeris.js](https://github.com/hamweather/aerisjs). This means that most of the work I'm doing on Aeris Interactive is bootstrapping, configuration, and integration.

Wire.js takes a lot of the grunt-work out of bootstrapping, and keeps all of my configuration where it belongs: in configuration files. So I can do something like this:

{% highlight javascript %}
// context/app.js
define({
  myView: {
    create: {
      module: 'views/baseView'
      args: [{
        template: 'hbars!templates/myTemplate.html'
      }]
    }
  }
});

// app.js
define(['wire!context/app'], function(ctx) {
  var app = {
    start: function($el) {
      ctx.myView.render().
        appendTo($el);
    }
  }

  return app;
});
{% endhighlight %}

Pretty cool, eh? I geek out on this kind of thing, so I've really enjoyed using Wire.js. Our code base is quite large, and includes many different modularized components. Wire.js provides much needed structure, and helps me keep my sanity while I'm working on this project.

## Using Almond.js

One of the requirements for the library I'm creating is to be able to access components within the global namespace. The goal is to make the library as simple to use as possible.

{% highlight html %}
<script src="builtLib.js"></script>
<script>
  myLib.TheAppImWorkingOn();
</script>
{% endhighlight %}

Generally I would use the [Almond.js](https://github.com/jrburke/almond) AMD shim to accomplish this. Almond replaces RequireJS's asynchrnous `require` method with a synchronous version.

{% highlight javascript %}

// Almond.js included here...

// My library included here...

// Requie
window.myLib = {
  TheAppImWorkingOn: require('app')
}

{% endhighlight %}

This gives me the best of both worlds: I have a repo with AMD modules for developers using RequireJS, and a traditional "global vars" library for users who don't want to mess with the whole AMD thing.

## Wire.js: why won't you play nicely with Almond.js?

I use Almond.js as part of the build process for the open source [Aeris.js](https://github.com/hamweather/aerisjs) library without problem. But when I tried to use Almond.js together on a project with Wire.js, and everything collapses. Almond.js failed to require the module, and I had no access to the global library objects.

This was really a bummer. Of course, I waited until large portions of the library were written until attempting a build. Ever try telling your boss, "yes, all of my tasks are done -- I just can't deliver anything this sprint"?

I couldn't for the life of me figure out what was going on. To be honest, I did'n't completely grok the libraries I was working with: Almond.js was some kind of magical synchronizing fairy in my mind, and I had already spent too many nights crying over RequireJS build configurations. I was done. I ended up including the full RequireJS library in my builds, using an ugly work-around to hide the asynchronous logic from the end-user.


## The culprit: the wire! AMD plugin

After a few months of living with an embarrassing hack, I woke up one morning and realized my problem: the `wire!` AMD plugin. Let's look back at how we used this:

 {% highlight javascript %}
 define(['wire!context/myApp.js'], function(ctx) {
    // myApp components are available as properties of `ctx`
 });
 {% endhighlight %}

So what is this doing behind the scenes? If you say "magic", you're only half right. Here's what the `wire!` plugin code looks like (*after some simplifications*):

{% highlight javascript %}
// wire.js
define(function() {
  // See http://requirejs.org/docs/plugins.html#api
  // for more on the AMD plugin API
  wire.load = function(amdModulePath, require, onload) {
    // Wire up the context
    wire(amdModulePath).
      // resolve with the wired context
      then(onload);
  });
  // ...
});
{% endhighlight %}

Pretty straightforward, eh? The key thing to note here, is that `wire.load` is asynchronous (it returns a [`Promise`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise)). Which means that our `wire!` AMD loader plugin is necessarily asynchronous. Which means that any module which uses the `wire!` plugin is necessarily asynchronous. And there ain't *nothing* no magical-synchronizing-Almond.js-fairy can do about it.


## The solution: stop using `wire!` (sort of)

So now the easy part: just stop using the `wire!` plugin, right? Because refactoring the initialization logic of large applications is easy, right? Right, guys...?

Getting rid of `wire!` posed two major problems:

1. How/where/when do I wire my Wire.js specs?
2. How does `r.js` know to build dependencies defined my my Wire.js specs?

In short, here's what I came up with:

### 1. How/where/when do I wire my Wire.js specs?

Getting rid of the `wire!` plugin means that I'll have to wire my specs programmatically. This means introducing some asynchronous behavior to my application initialization.

To handle the asynchronous initialization work, I created a `WiredModule` base class. It wires a context spec, and provides several event-hooks for subclasses to add their own initialization logic.

{% highlight javascript %}
define(['wire', 'underscore', 'backbone'], function(wire, _, Backbone) {
  var WiredModule = function(moduleSpec) {
    this.moduleSpec_ = moduleSpec;
  };
  // Mixin Backbone.Events (any event or pub/sub library would work fine)
  _.extend(WiredModule.prototype, Backbone.Events);

  WiredModule.prototype.initialize = function() {
    // Use Wire.js programmatically
    // See https://github.com/cujojs/wire/blob/master/docs/wire.md#amd
    wire(this.moduleSpec).
      then(function(wiredCtx) {
        // Module subclasses can hook into `wire:after`
        // to gain access to their wired context.
        this.trigger('wire:after', wiredCtx)

        // For any listeners who don't need to know
        // about the wiring logic
        this.trigger('initialize');
      }.bind(this));
  };

  return WiredModule;
});
{% endhighlight %}

A module subclass might look something like this:

{% highlight javascript %}
// context/animationModule.js
define({
  animationTimelineController: {
    create: {
      module: 'controllers/timelinecontroller',
      args: [{
        min: Date.now() - 1000 * 60 * 60,
        max: Date.now()
      }]
    }
  }
});

// modules/AnimationModule.js
define([
  'modules/WiredModule',
  'context/animationModule'
], function(WiredModule, animationModuleSpec) {
  var AnimationModule = function() {
    // Call the parent WiredModule with the animation module's
    // Wire.js spec
    WiredModule.call(this, animationModuleSpec);

    this.on('wire:after', function(ctx) {
      // Save wired objects to the module instance
      this.timelineController_ = ctx.animationTimelineController;
    });

    this.on('initialize', function() {
      this.timelineController_.render();
    });
  };
  // Inherit from the WiredModule
  AnimationModule.prototype = Object.create(WiredModule.prototype);

  return AnimationModule;
});
{% endhighlight %}

The asynchronous initialization code adds a little bit of complexity to our modules. But by using well-named events, we can easily handle the Module "lifecycle", while keeping the intent of our code clear.

### 2. How does `r.js` know to build dependencies defined my my Wire.js specs?

So, awesome -- we have our modules working, we got rid of that pesky asynchronous `wire!` plugin, it's time to run a build!

The r.js optimizer runs without a hitch. I turn gleefully to my browser, ready to reap the rewards of refactoring all of my modules.... and what's this?!

{% highlight bash %}
  Uncaught Error: undefined missing controllers/timelinecontroller
{% endhighlight %}

The `controllers/timelinecontroller` AMD module is missing from my build!

This is when I remember that I had been using the [wire-rjs-builder](https://github.com/pieter-vanderwerff/wire-rjs-builder.git) as my `wire!` plugin. This is a really handy project by [Pieter Vanderwerff](http://pieter.io/) which scans through your Wire.js spec during an r.js build, and adds any referenced module to the build. It was a lifesaver when I first found it. But now that I'm not using the `wire!` plugin, how do I make sure all of the modules referenced in my spec get added to the build?

What if we could use the dependency-optimizing features of the `wire!` plugin, without using the asynchonous wiring functionality?

Guess what? We can! I created a wrapper around the wire-rjs-builder, which prevents it from wiring specs, but still adds any referenced modules to builds.

{% highlight javascript %}
  // buildSpec.js
  define(['wire-rjs-builder'], function(rjsBuilder) {
    var buildSpec = {};

    buildSpec.load = function(wireSpec, parentRequire, onload, config) {
      // We're in an r.js optimizer build:
      // let the wire-rjs-builder do its thing
      if (config.isBuild) {
        rjsBuilder.load(wireSpec, parentRequire, onload, config);
      }
      else {
        // Otherwise, resolve with the raw spec.
        parentRequire([wireSpec], onload);
      }
    };

    // Use the rjsBuilder plugin for module optimization (r.js).
    buildSpec.write = rjsBuilder.write;

    return buildSpec;
  });
{% endhighlight %}

Our ne `buildSpec!` plugin acts like the `wire!` plugin during an r.js optimizer build, but otherwise it simply resolves with the raw spec object.

With a simple modification to my AnimationModule, I can fix my build-dependency issue:

{% highlight javascript %}
  // modules/AnimationModule.js
  define([
    'modules/WiredModule',

    // CHANGED:
    // Use the `buildSpec` plugin to load my Wire.js context
    'buildSpec!context/animationModule'
  ], function(WiredModule, animationModuleSpec) {
    var AnimationModule = function(userConfig) {
      // Pass the raw Wire.js spec object to the parent
      // WiredModule class
      WiredModule.call(this, animationModuleSpec);
    }
    // ...

    return AnimationModule;
{% endhighlight %}

My AnimationModule is loading in the raw Wire.js spec, but any dependencies defined in the spec will still be included in my build.


## What I learned

What did I learn from all of this?

1. There is no magical Almond.js synchronizing fairy
2. Async code is async code
3. Async code is a devious beast

I'm still really happy with Wire.js. Even with the amount of time I've spent trying to grok how it all works, I feel like it has saved me time in the long run, and made my code easier to read and more maintainable.

- - -

### BTW: My first blog post!

Every day I learn something new at work, and I'm always geeking out over some new library/coding-pattern/bug. Those closest to me will smile politely when I go on technical rants... but I feel like coding blog *might* be a better outlet.

I'd love to your feedback/complaints/ideas - you can find my contact info on my [github page](https://github.com/eschwartz/). Happy coding!