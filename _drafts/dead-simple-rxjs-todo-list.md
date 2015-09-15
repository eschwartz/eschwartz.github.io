---
layout: post
tags: [javascript, rxjs, reactivex, functional programming]
title: "A Dead-Simple Todo List with RxJS"
---

I've recently been playing around with [RxJS](https://github.com/Reactive-Extensions/RxJS). If you're not familiar with RxJS, I would suggest watching [this talk by Jafar Husain](https://youtu.be/XE692Clb5LU) about how Netflix used RxJS to build it's new front-end.

I'm really interested in trying to wrap my head around RxJS, and functional programming in general, just because it's so different than what I'm used to doing. I've read a ton of articles, and pored through the RxJS docs, but I had a really hard time implementing anything more than a simple snippet.

There is a TodoMVC example using [RxJS](https://github.com/cyclejs/todomvc-cycle), and I spent quite a bit of time trying to grok what was going on in there. The example Todo app just tries too hard to show off all the features, which makes it really tough to understand for a beginner.

After a many meeting between my head and the desk, I finally came up with a simple list view using RxJS and Cycle.js.

So in the interest of saving the brain cells of other developers, I present to you:

<h1 style="text-align:center; font-style: italic; padding: 40px;">A Dead-Simple Todo List with RxJS</h1>

## What is RxJS?

In short, RxJS is a library for working with asynchronous streams, which it calls "Observables". Let's, for example, take a look at a stream of click events in RxJS.

<a class="jsbin-embed" href="http://jsbin.com/zusicetiqa/embed?js">JS Bin on jsbin.com</a><script src="http://static.jsbin.com/js/embed.min.js?3.34.3"></script>

<small>*NOTE: This is a live example using [JS Bin](https://jsbin.com/). Click the 'Output' tab to test out the application.*</small>

What we've written is essentially an event-handler for a button click event. But the code looks a lot more like data-processing logic than event-handling logic. In fact, it can be quite helpful to think about RxJS observables as *asynchronous arrays*.


## Cool, but how do you code an actual application?

I'm glad you asked, because that happens to be the topic of this very blog post!

Let's start by taking a look at [Cycle.js](http://cycle.js.org/), a small application component for RxJS. Cycle.js will render a [virtual-dom](https://github.com/Matt-Esch/virtual-dom) from a stream of application states.

Let's try integrating Cycle.js with our button-click example.

<a class="jsbin-embed" href="http://jsbin.com/tayoci/embed?js&height=940px">JS Bin on jsbin.com</a><script src="http://static.jsbin.com/js/embed.min.js?3.34.3"></script>

As you can see, the core business logic is similar to our first example. The main differences are in:

* How we listen to user intentions (`DOM.get()`, instead of `Rx.Observable.fromEvent()`)
* How we send back views to the user (virtual-dom stream using `h()`, instead of direct manipulation with jQuery)


## Let's refactor

That `main()`` function is a little long, and I'm seeing view stuff right next to state stuff, which I don't really like. The [cycle.js docs propose a Model-View-Intent pattern](http://cycle.js.org/model-view-intent.html). Without going to much into it, I'll show you how that might look with this code.

<a class="jsbin-embed" href="http://jsbin.com/rafitu/embed?js&height=900px">JS Bin on jsbin.com</a><script src="http://static.jsbin.com/js/embed.min.js?3.34.3"></script>

Ah... much better, dontchya think?


## The Todo List

The [TodoMVC spec](https://github.com/tastejs/todomvc/blob/master/app-spec.md) requires a lot of things. But because we're making a *dead simple* todo list, I'm only going to require two things:

1. A user can add an item to their todo list, by typing text into a textbox
2. A user can remove an item from their list, by clicking a delete button next to the item.

We'll also make the app <s>ugly</s> semantic, so we don't have to worry about CSS or strange markup.


### Requirement 1: A user can add an item to their todo list

If you look at our even-numbers button example from earlier, you'll see we already have the bones for a user to add something to a list view. Let's see if we can just replace those buttons with a text input.

<a class="jsbin-embed" href="http://jsbin.com/xilivo/embed?js&height=900px">JS Bin on jsbin.com</a><script src="http://static.jsbin.com/js/embed.min.js?3.34.3"></script>