---
layout: post
tags : [zf2, zend framework 2, doctrine, jms serializer, REST api]
title: "Implemented a PUT endpoint in Zend Framework 2"
excerpt: "It never ceases to amaze me, how seemingly common problems start to look like they must be fringe cases..."
---
It never ceases to amaze me, how seemingly common problems start to look like they must be fringe cases once you start working on them. This week, me and my colleague [Seth Miller](http://four43.com/) were tasked with putting together a RESTful HTTP PUT endpoint, to accept partial updates to a data model.

A quick refresher: PUT is one of four core HTTP methods used to interact with a RESTful API. For the sake of this blog post, let's say we're working with a Beer and Breweries API. Our beer endpoints would look like this:

* GET /beers[/:id]
    * Responds with a list of beers, or a single beer with the matching id.
* POST /beers
    * Creates a new beer, with data the provided by the client
* PUT /beers/:id
    * Makes changes to an an existing beer, with data provided by the client
* DELETE /beers/:id
    * Deletes the beer with the provided :id

For this project, we're using Zend Framework 2 (v2.3). We're also using a couple other nifty tools to make our lives much easier:

1. [*Doctrine ORM*](http://www.doctrine-project.org/projects/orm.html): An *Object Relational Mapper*, which is a fancy way of saying that it handles saving and retrieving models from our MySQL database. We use annotations to tell Doctrine which models are associated with which database tables, the types of each field, and relationships between models.
2. [*JMS Serializer*](http://jmsyst.com/libs/serializer): Allows you to [configure](http://jmsyst.com/libs/serializer/master/reference/annotations) exactly how you want your models serialized into json. You can use your same serialization rules to convert json back into model objects.

Between these two tools, am I able to configure-and-forget the details of my incoming and outgoing transactions.

 ![Serializer / ORM flow diagram]({{ site.url }}/assets/posts/zf2-partial-model-updates/serializer-orm-flow.png)

I really like this workflow, because it keeps my controllers skinny, and focused on the task at hand. It also keeps my models clean and stupid, as they should be.

## Time to update a model (this should be easy, right?)

So I'm super happy with this setup, and ready to start banging out some quick endpoints. Here are some easy ones:

{% highlight php %}
use Zend\Mvc\Controller\AbstractRestfulController;
use Zend\View\Model\JsonModel;

class BeerRestController extends AbstractRestfulController {

  /** @var \Doctrine\ORM\EntityManager */
  private $em;

  /** @var \Doctrine\ORM\EntityRepository */
  private $beerRepo;

  /** @var \JMS\Serializer\Serializer */
  private $serializer;

  public function __constructor() {
    $sm = $this->getServiceLocator();

    // You'll have to configure these services in your module
    $this->em = $sm->get('doctrine.entitymanager.orm_default');
    $this->beerRepo = $this->em->getRepository('MyApp\Model\Beer');

    $this->serializer = $sm->get('jms_serializer');
  }

  /** GET /beers/:id */
  public function get($id) {
    // Use Doctrine ORM to create a beer model
    // from a db record with a matching id.
    $beer = $this->beerRepo->findById($id);

    // Serialize the MyApp\Model\Beer model into json,
    // and send it back to the client
    $beerJson = $this->serializer->serialize($beer, 'json');

    return new JsonModel(json_decode($beerJson));
    // JsonModel expects a php array (not a json string),
    // so we have to re-deserialize the json into a plain array.
    // I'll show you in the next post how to abstract this out, so you
    // don't have to do this every time.
  }

  /** POST /beers */
  public function create($data) {
    // Create a MyApp\Model\Beer model from
    // the client's json request
    $beerJson = json_encode($data);
    $beer = $this->serializer->deserialize($beerJson, 'MyApp\Model\Beer', 'json');

    // Save the beer to the db
    $this->em->persist($beer);
    $this->em->flush();

    // Send the updated beer model (with id) back to the client.
    $updatedBeerJson = $this->serializer->serialize($beer, 'json');
    return new JsonModel(json_decode($updatedBeerJson));
  }

}
{% endhighlight %}

Besides a couple small quirks between ZF2 and the JMS Serializer, this is all pretty slick, and works just as you would expect.

Cool, so let's update a beer.

{% highlight php %}
class BeerRestController extends AbstractRestController {
// ...

  /** PUT /beers/:id */
  public function update($id, $data) {
    // Create a beer model from the client's data
    $updatedBeer = $this->serializer->deserialize(json_encode($data), 'MyApp\Model\Beer', 'json');

    // Merge the client's beer model with the existing model
    $this->em->merge($updatedBeer);
    $this->em->flush();

    // Send the updated beer model (with id) back to the client.
    $updatedBeerJson = $this->serializer->serialize($beer, 'json');
    return new JsonModel(json_decode($updatedBeerJson));
  }

}
{% endhighlight %}

That looks like it should work. But in fact, we get a MySQL error for trying to insert null into a NOT NULL field. So what's really happening here? Let's take another look at the controller:


{% highlight php %}
class BeerRestController extends AbstractRestController {
// ...

  /** PUT /beers/:id */
  public function update($id, $data) {
    /**
     * User passes in some new data for a beer model.
     * $data = array(
     *   'id' => 123,
     *   'ibu' => 70
     * );
     */

    $updatedBeer = $this->serializer->deserialize(json_encode($data), 'MyApp\Model\Beer', 'json');
    /**
     * JMS Serializer coverts the raw data into a Beer model,
     * with some missing fields:
     *
     * object(MyApp\Model\Beer)
     *  'id' => 1
     *  'name' => null
     *  'brewery_id' => null
     *  'ibu' => 70
     *  'abv' => null
     */

    $this->em->merge($updatedBeer);
    $this->em->flush();
    /**
     * Doctrine updates the existing beer model
     * with any defined fields in the $updatedBeerModel,
     * including the fields which are set to null.
     *
     * Saving null fields to the db makes MySQL angry,
     * and everything comes crashing down.
     */

    // ...
  }

}
{% endhighlight %}

So we've found ourselves in a doozy of a pickle here. We have these awesome tools, but we somehow can't figure out how to perform this common task.

Doctrine can't really be to blame here. We're giving it an object with null values, and it's saving that object to the db, exactly as you'd suspect. The problem is that the serializer creates an entirely new model with our data, when we really want it update an existing model. In other words, I'd like to do something like this:

{% highlight php %}
  // ...
  $data = array(
    'id' => 123,
    'ibu' => 70
  );
  $beer = $this->beerRepo->findById(123);

  // Deserialize our data "on top of" an existing beer model,
  // only updating fields defined in the json object.
  $this->serializer->deserialize($data, $beer, 'json');

  $this->em->persist($beer);
{% endhighlight %}

Alas, this is not how the serializer works.

[My colleague](http://four43.com/), Seth, and I spent hours looking for a work-around. We started with the Serializer's (pathetically incomplete) documentation -- nothing. Then Stack Overflow -- nothing. Then the serializer source code -- nothing. Really, are we the only developers who have ever tried to update a model with the JMS Serializer?

Finally, [Seth](http://four43.com/) happened on a issue in the serializer's github repo, ["Allow Constructed Object to be Passed to Deserialize"](https://github.com/schmittjoh/serializer/issues/79). That sounds promising! And what's this? A merged pull request? There is light at the end of the tunnel!

But did the pull request allow deserialize to accept an object? No. Did it explain (in English) how to do so? Definately not.

I'll spare you all of the frustration and tears that followed, but it was eventually [Seth](http://four43.com/) who found it: a line of code in the pull request, deep inside some test code, of all places:

{% highlight php %}
$objectConstructor = new InitializedObjectConstructor(new UnserializeObjectConstructor());
{% endhighlight %}

What the heck's an `InitializedObjectConstructor`? We tried pulling it into our project, and the file couldn't even be loaded. Turns out it's a test fixture, created solely for that one test, then hidden away from the world.

But for you, dear reader, I will explain (in English) how to use this thing. First we copy/pasted the [`InitializedObjectConstructor`](https://github.com/schmittjoh/serializer/blob/master/tests/JMS/Serializer/Tests/Fixtures/InitializedObjectConstructor.php) into our project. We then used it in creating our Serializer service:

{% highlight php %}
// module.config.php
// ...
    'service_manager' => array(
      'factories' => array(
        // Create a jms serializer service,
        // configured to use the InitializedObjectConstructor
        'serializer' => function() {
          // ...
          $defaultObjCtor = new \JMS\Serializer\Construction\UnserializeObjectConstructor();
          $initializedObjCtor = new \MyApp\path\to\copy\and\pasted\InitializedObjectCtor($defaultObjCtor);

          return \JMS\Serializer\SerializerBuilder::create()
            ->setObjectConstructor($initializedObjCtor)
            ->build();
        }
      ),
    ),
// ...
{% endhighlight %}

We then add a few magic lines to our `update` action (don't ask what they do, just be happy they work);

{% highlight php %}

  /** PUT /beers/:id */
public function update($id, $data) {
  // Create a deserialization context, targeting the existing beer model
  $context = new \JMS\Serializer\DeserializationContext();
  $context->attributes->set('target', $user);

  // Deserialize the data "on to" to the existing beer model
  $this->serializer->deserialize(json_encode($data), 'MyApp\Model\Beer', 'json', $context);

  // Save the updated beer model
  $this->em->persist($updatedBeer);
  $this->em->flush();

  // ...
}
{% endhighlight %}

Et voila!

Someday, I imagine all of this kind of standard blueprint code will be much easier to implement. I mean really, this kind of simple API endpoint should be like falling off a log. Until then, we'll have to take some time to really get to know our tools, even if it means searching through tests to figure how to use them.