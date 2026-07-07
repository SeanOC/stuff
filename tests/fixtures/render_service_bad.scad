// Intentional-failure fixture for the native render service (st-065).
//
// NOT a model — never exported or shown in the gallery. It exists so the
// render service's failure path can be proven end-to-end: openscad hits
// this failed assert, exits non-zero, and the service must return
// 500 {ok:false, errorMessage} and NEVER an STL. The trailing cube keeps
// it a syntactically valid file so the *only* failure is the assert.
assert(false, "render-service failure-path fixture (st-065)");
cube(1);
