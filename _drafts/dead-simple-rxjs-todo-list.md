---
layout: post
tags: [javascript, rxjs, reactivex, functional programming]
title: "A Dead-Simple Todo List with RxJS and Cycle.js"
---

I've recently been playing around with [RxJS](https://github.com/Reactive-Extensions/RxJS). If you're not familiar with RxJS, I would suggest watching [this talk by Jafar Husain](https://youtu.be/XE692Clb5LU) about how Netflix used RxJS to build it's new front-end.

In short, RxJS is a library for working with asynchronous streams, which it calls "Observables". Let's, for example, take a look at a stream of click events in RxJS.

<div class="wide">
    <a class="jsbin-embed" href="http://jsbin.com/zusicetiqa/embed?js,output">JS Bin on jsbin.com</a><script src="http://static.jsbin.com/js/embed.min.js?3.34.3"></script>
</div>

What we've written is essentially an event-handler for a button click event. But the code looks a lot more like data-processing logic than event-handling logic. In fact, it can be quite helpful to think about RxJS observables as *asynchronous arrays*.


## Cool, but how do you code an actual application?

I'm glad you asked, because that happens to be the topic of this very blog post!

Let's start by taking a look at [Cycle.js](http://cycle.js.org/), a small application component for RxJS. Cycle.js will render a [virtual-dom](https://github.com/Matt-Esch/virtual-dom) from a stream of application states.

Let's try integrating Cycle.js with our button-click example.

<div class="wide">
<a class="jsbin-embed" href="http://jsbin.com/tayoci/embed?js,output">RxJS Click Stream Example on jsbin.com</a><script src="http://static.jsbin.com/js/embed.min.js?3.34.3"></script>
</div>