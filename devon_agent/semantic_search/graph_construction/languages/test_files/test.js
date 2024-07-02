// Import statement
import { useState, useEffect } from 'react';

// Function declaration
function normalFunction(param1, param2) {
    return param1 + param2;
}

// Arrow function with implicit return
const arrowFunction = (x, y) => x * y;

// Arrow function with block body
const complexArrowFunction = async (a, b) => {
    const result = await someAsyncOperation(a, b);
    return result * 2;
};

// Class declaration
class MyClass {
    constructor(name) {
        this.name = name;
    }

    // Method
    sayHello() {
        console.log(`Hello, ${this.name}!`);
    }

    // Static method
    static staticMethod() {
        return 'This is a static method';
    }

    // Getter
    get upperCaseName() {
        return this.name.toUpperCase();
    }

    // Setter
    set age(value) {
        if (value < 0) throw new Error('Age cannot be negative');
        this._age = value;
    }
}

// Object literal with method definitions
const obj = {
    methodOne() {
        return 'Method One';
    },
    methodTwo: function() {
        return 'Method Two';
    },
    arrowMethod: () => 'Arrow Method'
};

// Variable declarations
var oldVar = 'Old var declaration';
let modernLet = 'Modern let declaration';
const constantValue = 'Constant value';

// Destructuring assignment
const { property1, property2 } = someObject;
const [item1, item2] = someArray;

// Default parameters and rest parameters
function defaultAndRest(param1 = 'default', ...restParams) {
    console.log(param1, restParams);
}

// Async function declaration
async function fetchData() {
    const response = await fetch('https://api.example.com/data');
    return response.json();
}

// Generator function
function* generatorFunction() {
    yield 1;
    yield 2;
    yield 3;
}

// IIFE (Immediately Invoked Function Expression)
(function() {
    console.log('IIFE executed');
})();

// Higher-order function
function higherOrder(callback) {
    return function(value) {
        return callback(value);
    };
}

// Promise
const myPromise = new Promise((resolve, reject) => {
    setTimeout(() => resolve('Promise resolved'), 1000);
});

// Try-catch block
try {
    throw new Error('Test error');
} catch (error) {
    console.error(error);
} finally {
    console.log('Finally block executed');
}

// Switch statement
switch (someValue) {
    case 1:
        console.log('One');
        break;
    case 2:
        console.log('Two');
        break;
    default:
        console.log('Other');
}

// ES6 Module export
export { normalFunction, MyClass };
export default arrowFunction;