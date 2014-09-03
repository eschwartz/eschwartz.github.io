---
layout: post
tags : [javascript, Wire.js, Almond.js, RequireJS, IoC, dependency injection]
title: "Wire.js builds using the Almond.js AMD shim"
---
I have been using [Wire.js](https://github.com/cujojs/wire) while building a weather maps application for my [employer](http://www.hamweather.com/), dubbed *Aeris Interactive*. If you're not familiar with Wire.js, here's a short summary from their github page:

>Wire is an Inversion of Control Container for Javascript apps, and acts as the Application Composition layer for cujoJS.

>Wire provides architectural plumbing that allows you to create and manage application components, and to connect those components together in loosely coupled and non-invasive ways. Consequently, your components will be more modular, easier to unit test and refactor, and your application will be easier to evolve and maintain.

In other words, Wire.js does dependency injection for javascript. So I can do something like this:

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
  // ctx.myView is an instance of 'views/baseView',
  // created with the 'templates/myTemplate.html.hbs' template
});
{% endhighlight %}

Pretty cool, eh? I geek out on this kind of thing, so I've really enjoyed using Wire.js. Our code base is quite large, and includes many different modularized components -- it's really nice to be able to configure all of these components in one place.

## Using Almond.js

One of the requirements for the library I'm creating is to be able to access components within the global namespace. This means users of the library won't need to mess around with RequireJS.

{% highlight html %}
<script src="builtLib.js"></script>
<script>
  myLib.TheAppImWorkingOn();
</script>
{% endhighlight %}

Generally I would use the [Almond.js](https://github.com/jrburke/almond) AMD shim to accomplish this. I just include Almond.js in my optimized build, then wrap it like so:

{% highlight javascript %}
(function(root) {
  // Almond.js included here
  // My library included here
  root.myLib = {
    TheAppImWorkingOn: require('app')
  }
}(window));
{% endhighlight %}

This gives me the best of both worlds: I have a repo with AMD modules for developers using RequireJS, and a traditional "global vars" library for users who don't want to mess with the whole AMD thing.

## Wire.js: why won't you play nicely with Almond.js?

I had been using this Almond.js setup for my [Aeris.js](https://github.com/hamweather/aerisjs) without problem. But then I tried to use Almond.js together on a project with Wire.js --- not happening. Almond.js failed to require the module, and I had no access to the global library objects.

This was really a bummer. Of course, I waited until large portions of the library were written until attempting a build. Ever try telling your boss, "yes, all of my tasks are done -- I just can't deliver anything this sprint"?

I couldn't for the life of me figure out what was going on. At this point, Almond.js was some kind of magical synchronizing fairy in my mind, and I had already spent too many nights crying over RequireJS build configurations. I was done. I threw in an ugly work-around using the full RequireJS library in builds, and brushed it off my shoulders.


## The culprit: the wire! AMD plugin

After a few months of living with an embarrassing hack, I woke one morning and realized my problem: the `wire!` AMD plugin. Let's look back at how we used this:

 {% highlight javascript %}
 define(['wire!context/myApp.js'], function(ctx) {
    // myApp components are available as properties of `ctx`
 });
 {% endhighlight %}

So what is this doing behind the scenes? If you say "magic", you're only half write. Here's what the `wire!` plugin code looks like (*after some simplifications*):

{% highlight javascript %}
// wire.js
define(function() {
  // ...
  wire.load = function(amdModulePath, require, onload) {
    // Wire up the context
    wire(amdModulePath).
      // resolve with the wired context
      then(onload);
  });
  // ...
});
{% endhighlight %}

Pretty straightforward, eh? The key thing to note here, is that `wire()` is asynchronous (it returns a `Promise`). Which means that our `wire!` AMD loader plugin is necessarily asynchronous. Which means that any module which uses the `wire!` plugin is necessarily asynchronous. And there ain't nothing no magical synchronizing Almond.js fairy can do about it.


## The solution: stop using `wire!` (sort of)

So now the easy part: just stop using the `wire!` plugin, right? Because refactoring the initialization logic of large applications is easy, right? Right, guys...?

Getting rid of `wire!` posed two major problems:

1. How/where/when do I wire my Wire.js specs?
2. How does `r.js` know to build dependencies defined my my Wire.js specs?

In short, here's what I came up with:

### 1. How/where/when do I wire my Wire.js specs?

Getting rid of the `wire!` plugin means that I'll have to wire my specs pragmatically. This means introducing some asynchronous behavior to my application initialization.

To handle the asynchronous initialization work, I created a WiredModule. It wires the context spec, and provides several event-hooks for subclasses to add their own initialization logic.

{% highlight javascript %}
define(['wire'], function(wire) {
  var WiredModule = function(moduleSpec) {
    this.moduleSpec_ = moduleSpec;
  };
  // Mixin Backbone.Events (any event or pub/sub library would work fine)
  _.extend(WiredModule.prototype, Backbone.Events);

  WiredModule.prototype.initialize = function() {
    // Use Wire.js programmatically
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
      args: [
        min: Date.now() - 1000 * 60 * 60,
        max: Date.now()
      ]
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

The asynchronous initialization code adds a little bit of complexity to our modules, but by using events, we can keep the intent of the code clear.

### 2. How does `r.js` know to build dependencies defined my my Wire.js specs?

So, awesome -- we have our modules working, we got rid of that pesky `wire!` plugin, it's time to run a build!

The r.js optimizer runs without a hitch. I turn gleefully to my browser, ready to reap the rewards of refactoring all of my modules.... and what's this?!

{% highlight bash %}
  Uncaught Error: undefined missing controllers/timelinecontroller
{% endhighlight %}

The `controllers/timelinecontroller` AMD module is missing from my build!

This is when I remember that I had been using the [wire-rjs-builder](https://github.com/pieter-vanderwerff/wire-rjs-builder.git) as my `wire!` plugin. This is a really handy project by [Pieter Vanderwerff](http://pieter.io/) which scans through your Wire.js spec during an r.js build, and adds any referenced module to the build. It was a lifesaver when I first found it. But now that I'm not using the `wire!` problem, how do I make sure all of the modules referenced in my spec get added to the build?

What if we could still use the wire-rjs-builder AMD plugin, but only for builds?

So I created a wrapper around the wire-rjs-builder, which prevents it from wiring specs, but still adds any referenced modules to builds.

{% highlight javascript %}
  // buildSpec.js
  define(['wire-rjs-builder'], function(rjsBuilder) {
    var buildSpec = {};

    buildSpec.load = function(wireSpec, parentRequire, onload, config) {
      // We're in an r.js build:
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

The `buildSpec!` acts like the `wire!` plugin during a build, but otherwise it just resolved with the raw spec object.

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

======

### My first blog post!

Every day I learn something new at work, and I'm always geeking out over some new library/coding-pattern/bug. And while my wife is very kind to humors my long technical rants, I feel a coding blog *might* be a more appropriate outlet.

I'd love to your feedback/complaints/ideas. Happy coding!