function t(t,e,i,s){var r,o=arguments.length,n=o<3?e:null===s?s=Object.getOwnPropertyDescriptor(e,i):s;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)n=Reflect.decorate(t,e,i,s);else for(var a=t.length-1;a>=0;a--)(r=t[a])&&(n=(o<3?r(n):o>3?r(e,i,n):r(e,i))||n);return o>3&&n&&Object.defineProperty(e,i,n),n}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const e=globalThis,i=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,s=Symbol(),r=new WeakMap;let o=class{constructor(t,e,i){if(this._$cssResult$=!0,i!==s)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(i&&void 0===t){const i=void 0!==e&&1===e.length;i&&(t=r.get(e)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),i&&r.set(e,t))}return t}toString(){return this.cssText}};const n=(t,...e)=>{const i=1===t.length?t[0]:e.reduce((e,i,s)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+t[s+1],t[0]);return new o(i,t,s)},a=i?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const i of t.cssRules)e+=i.cssText;return(t=>new o("string"==typeof t?t:t+"",void 0,s))(e)})(t):t,{is:h,defineProperty:l,getOwnPropertyDescriptor:c,getOwnPropertyNames:d,getOwnPropertySymbols:p,getPrototypeOf:u}=Object,m=globalThis,g=m.trustedTypes,f=g?g.emptyScript:"",v=m.reactiveElementPolyfillSupport,$=(t,e)=>t,y={toAttribute(t,e){switch(e){case Boolean:t=t?f:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let i=t;switch(e){case Boolean:i=null!==t;break;case Number:i=null===t?null:Number(t);break;case Object:case Array:try{i=JSON.parse(t)}catch(t){i=null}}return i}},b=(t,e)=>!h(t,e),w={attribute:!0,type:String,converter:y,reflect:!1,useDefault:!1,hasChanged:b};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),m.litPropertyMetadata??=new WeakMap;let _=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=w){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const i=Symbol(),s=this.getPropertyDescriptor(t,i,e);void 0!==s&&l(this.prototype,t,s)}}static getPropertyDescriptor(t,e,i){const{get:s,set:r}=c(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:s,set(e){const o=s?.call(this);r?.call(this,e),this.requestUpdate(t,o,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??w}static _$Ei(){if(this.hasOwnProperty($("elementProperties")))return;const t=u(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty($("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty($("properties"))){const t=this.properties,e=[...d(t),...p(t)];for(const i of e)this.createProperty(i,t[i])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,i]of e)this.elementProperties.set(t,i)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const i=this._$Eu(t,e);void 0!==i&&this._$Eh.set(i,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const i=new Set(t.flat(1/0).reverse());for(const t of i)e.unshift(a(t))}else void 0!==t&&e.push(a(t));return e}static _$Eu(t,e){const i=e.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const i of e.keys())this.hasOwnProperty(i)&&(t.set(i,this[i]),delete this[i]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((t,s)=>{if(i)t.adoptedStyleSheets=s.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const i of s){const s=document.createElement("style"),r=e.litNonce;void 0!==r&&s.setAttribute("nonce",r),s.textContent=i.cssText,t.appendChild(s)}})(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,i){this._$AK(t,i)}_$ET(t,e){const i=this.constructor.elementProperties.get(t),s=this.constructor._$Eu(t,i);if(void 0!==s&&!0===i.reflect){const r=(void 0!==i.converter?.toAttribute?i.converter:y).toAttribute(e,i.type);this._$Em=t,null==r?this.removeAttribute(s):this.setAttribute(s,r),this._$Em=null}}_$AK(t,e){const i=this.constructor,s=i._$Eh.get(t);if(void 0!==s&&this._$Em!==s){const t=i.getPropertyOptions(s),r="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:y;this._$Em=s;const o=r.fromAttribute(e,t.type);this[s]=o??this._$Ej?.get(s)??o,this._$Em=null}}requestUpdate(t,e,i,s=!1,r){if(void 0!==t){const o=this.constructor;if(!1===s&&(r=this[t]),i??=o.getPropertyOptions(t),!((i.hasChanged??b)(r,e)||i.useDefault&&i.reflect&&r===this._$Ej?.get(t)&&!this.hasAttribute(o._$Eu(t,i))))return;this.C(t,e,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:i,reflect:s,wrapped:r},o){i&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,o??e??this[t]),!0!==r||void 0!==o)||(this._$AL.has(t)||(this.hasUpdated||i||(e=void 0),this._$AL.set(t,e)),!0===s&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,i]of t){const{wrapped:t}=i,s=this[e];!0!==t||this._$AL.has(e)||void 0===s||this.C(e,void 0,i,s)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};_.elementStyles=[],_.shadowRootOptions={mode:"open"},_[$("elementProperties")]=new Map,_[$("finalized")]=new Map,v?.({ReactiveElement:_}),(m.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const A=globalThis,x=t=>t,k=A.trustedTypes,S=k?k.createPolicy("lit-html",{createHTML:t=>t}):void 0,E="$lit$",z=`lit$${Math.random().toFixed(9).slice(2)}$`,C="?"+z,P=`<${C}>`,M=document,T=()=>M.createComment(""),O=t=>null===t||"object"!=typeof t&&"function"!=typeof t,R=Array.isArray,U="[ \t\n\f\r]",N=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,H=/-->/g,D=/>/g,L=RegExp(`>|${U}(?:([^\\s"'>=/]+)(${U}*=${U}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),j=/'/g,I=/"/g,B=/^(?:script|style|textarea|title)$/i,V=t=>(e,...i)=>({_$litType$:t,strings:e,values:i}),q=V(1),W=V(2),Z=Symbol.for("lit-noChange"),F=Symbol.for("lit-nothing"),K=new WeakMap,G=M.createTreeWalker(M,129);function X(t,e){if(!R(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==S?S.createHTML(e):e}const J=(t,e)=>{const i=t.length-1,s=[];let r,o=2===e?"<svg>":3===e?"<math>":"",n=N;for(let e=0;e<i;e++){const i=t[e];let a,h,l=-1,c=0;for(;c<i.length&&(n.lastIndex=c,h=n.exec(i),null!==h);)c=n.lastIndex,n===N?"!--"===h[1]?n=H:void 0!==h[1]?n=D:void 0!==h[2]?(B.test(h[2])&&(r=RegExp("</"+h[2],"g")),n=L):void 0!==h[3]&&(n=L):n===L?">"===h[0]?(n=r??N,l=-1):void 0===h[1]?l=-2:(l=n.lastIndex-h[2].length,a=h[1],n=void 0===h[3]?L:'"'===h[3]?I:j):n===I||n===j?n=L:n===H||n===D?n=N:(n=L,r=void 0);const d=n===L&&t[e+1].startsWith("/>")?" ":"";o+=n===N?i+P:l>=0?(s.push(a),i.slice(0,l)+E+i.slice(l)+z+d):i+z+(-2===l?e:d)}return[X(t,o+(t[i]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),s]};class Q{constructor({strings:t,_$litType$:e},i){let s;this.parts=[];let r=0,o=0;const n=t.length-1,a=this.parts,[h,l]=J(t,e);if(this.el=Q.createElement(h,i),G.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(s=G.nextNode())&&a.length<n;){if(1===s.nodeType){if(s.hasAttributes())for(const t of s.getAttributeNames())if(t.endsWith(E)){const e=l[o++],i=s.getAttribute(t).split(z),n=/([.?@])?(.*)/.exec(e);a.push({type:1,index:r,name:n[2],strings:i,ctor:"."===n[1]?st:"?"===n[1]?rt:"@"===n[1]?ot:it}),s.removeAttribute(t)}else t.startsWith(z)&&(a.push({type:6,index:r}),s.removeAttribute(t));if(B.test(s.tagName)){const t=s.textContent.split(z),e=t.length-1;if(e>0){s.textContent=k?k.emptyScript:"";for(let i=0;i<e;i++)s.append(t[i],T()),G.nextNode(),a.push({type:2,index:++r});s.append(t[e],T())}}}else if(8===s.nodeType)if(s.data===C)a.push({type:2,index:r});else{let t=-1;for(;-1!==(t=s.data.indexOf(z,t+1));)a.push({type:7,index:r}),t+=z.length-1}r++}}static createElement(t,e){const i=M.createElement("template");return i.innerHTML=t,i}}function Y(t,e,i=t,s){if(e===Z)return e;let r=void 0!==s?i._$Co?.[s]:i._$Cl;const o=O(e)?void 0:e._$litDirective$;return r?.constructor!==o&&(r?._$AO?.(!1),void 0===o?r=void 0:(r=new o(t),r._$AT(t,i,s)),void 0!==s?(i._$Co??=[])[s]=r:i._$Cl=r),void 0!==r&&(e=Y(t,r._$AS(t,e.values),r,s)),e}class tt{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:i}=this._$AD,s=(t?.creationScope??M).importNode(e,!0);G.currentNode=s;let r=G.nextNode(),o=0,n=0,a=i[0];for(;void 0!==a;){if(o===a.index){let e;2===a.type?e=new et(r,r.nextSibling,this,t):1===a.type?e=new a.ctor(r,a.name,a.strings,this,t):6===a.type&&(e=new nt(r,this,t)),this._$AV.push(e),a=i[++n]}o!==a?.index&&(r=G.nextNode(),o++)}return G.currentNode=M,s}p(t){let e=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(t,i,e),e+=i.strings.length-2):i._$AI(t[e])),e++}}class et{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,i,s){this.type=2,this._$AH=F,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=i,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=Y(this,t,e),O(t)?t===F||null==t||""===t?(this._$AH!==F&&this._$AR(),this._$AH=F):t!==this._$AH&&t!==Z&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>R(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==F&&O(this._$AH)?this._$AA.nextSibling.data=t:this.T(M.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:i}=t,s="number"==typeof i?this._$AC(t):(void 0===i.el&&(i.el=Q.createElement(X(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===s)this._$AH.p(e);else{const t=new tt(s,this),i=t.u(this.options);t.p(e),this.T(i),this._$AH=t}}_$AC(t){let e=K.get(t.strings);return void 0===e&&K.set(t.strings,e=new Q(t)),e}k(t){R(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let i,s=0;for(const r of t)s===e.length?e.push(i=new et(this.O(T()),this.O(T()),this,this.options)):i=e[s],i._$AI(r),s++;s<e.length&&(this._$AR(i&&i._$AB.nextSibling,s),e.length=s)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=x(t).nextSibling;x(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class it{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,i,s,r){this.type=1,this._$AH=F,this._$AN=void 0,this.element=t,this.name=e,this._$AM=s,this.options=r,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=F}_$AI(t,e=this,i,s){const r=this.strings;let o=!1;if(void 0===r)t=Y(this,t,e,0),o=!O(t)||t!==this._$AH&&t!==Z,o&&(this._$AH=t);else{const s=t;let n,a;for(t=r[0],n=0;n<r.length-1;n++)a=Y(this,s[i+n],e,n),a===Z&&(a=this._$AH[n]),o||=!O(a)||a!==this._$AH[n],a===F?t=F:t!==F&&(t+=(a??"")+r[n+1]),this._$AH[n]=a}o&&!s&&this.j(t)}j(t){t===F?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class st extends it{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===F?void 0:t}}class rt extends it{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==F)}}class ot extends it{constructor(t,e,i,s,r){super(t,e,i,s,r),this.type=5}_$AI(t,e=this){if((t=Y(this,t,e,0)??F)===Z)return;const i=this._$AH,s=t===F&&i!==F||t.capture!==i.capture||t.once!==i.once||t.passive!==i.passive,r=t!==F&&(i===F||s);s&&this.element.removeEventListener(this.name,this,i),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class nt{constructor(t,e,i){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(t){Y(this,t)}}const at=A.litHtmlPolyfillSupport;at?.(Q,et),(A.litHtmlVersions??=[]).push("3.3.2");const ht=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class lt extends _{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,i)=>{const s=i?.renderBefore??e;let r=s._$litPart$;if(void 0===r){const t=i?.renderBefore??null;s._$litPart$=r=new et(e.insertBefore(T(),t),t,void 0,i??{})}return r._$AI(t),r})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return Z}}lt._$litElement$=!0,lt.finalized=!0,ht.litElementHydrateSupport?.({LitElement:lt});const ct=ht.litElementPolyfillSupport;ct?.({LitElement:lt}),(ht.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const dt={attribute:!0,type:String,converter:y,reflect:!1,hasChanged:b},pt=(t=dt,e,i)=>{const{kind:s,metadata:r}=i;let o=globalThis.litPropertyMetadata.get(r);if(void 0===o&&globalThis.litPropertyMetadata.set(r,o=new Map),"setter"===s&&((t=Object.create(t)).wrapped=!0),o.set(i.name,t),"accessor"===s){const{name:s}=i;return{set(i){const r=e.get.call(this);e.set.call(this,i),this.requestUpdate(s,r,t,!0,i)},init(e){return void 0!==e&&this.C(s,void 0,t,e),e}}}if("setter"===s){const{name:s}=i;return function(i){const r=this[s];e.call(this,i),this.requestUpdate(s,r,t,!0,i)}}throw Error("Unsupported decorator location: "+s)};function ut(t){return(e,i)=>"object"==typeof i?pt(t,e,i):((t,e,i)=>{const s=e.hasOwnProperty(i);return e.constructor.createProperty(i,t),s?Object.getOwnPropertyDescriptor(e,i):void 0})(t,e,i)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function mt(t){return ut({...t,state:!0,attribute:!1})}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const gt="zoneminder",ft=5e3,vt=[1,4,16];let $t,yt=!1;function bt(t){return t?.attributes.friendly_name??t?.entity_id??""}class wt{constructor(t){const e=t.config?.time_zone,i=t.locale?.language??navigator.language,s="12"===t.locale?.time_format||"24"!==t.locale?.time_format&&void 0;this.time=new Intl.DateTimeFormat(i,{timeZone:e,hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:s}),this.hour=new Intl.DateTimeFormat(i,{timeZone:e,hour:"numeric",hour12:s}),this.hourNumber=new Intl.DateTimeFormat("en-GB",{timeZone:e,hour:"2-digit",hour12:!1}),this.day=new Intl.DateTimeFormat(i,{timeZone:e,weekday:"short"}),this.dayKey=new Intl.DateTimeFormat("en-CA",{timeZone:e,year:"numeric",month:"2-digit",day:"2-digit"})}formatTime(t){return this.time.format(t)}formatMoment(t){return this.dayKey.format(t)===this.dayKey.format(Date.now())?this.formatTime(t):`${this.day.format(t)} ${this.formatTime(t)}`}ticks(t,e){const i=[],s=36e5;for(let r=Math.ceil(t/s)*s;r<=e;r+=s){const t=Number(this.hourNumber.format(r))%24;t%6==0&&i.push({t:r,label:0===t?this.day.format(r):this.hour.format(r),midnight:0===t})}return i}}const _t=n`
  :host {
    --zm-asphalt: #182026;
    --zm-kerb: #232c33;
    --zm-concrete: #7e8890;
    --zm-fog: #e3e7e9;
    --zm-tape: #3e6e8c;
    --zm-sodium: #f0a23b;
    --zm-font:
      "Barlow Semi Condensed", "Roboto Condensed", system-ui, sans-serif;
  }
`;class At extends lt{constructor(){super(...arguments),this.entity="",this.hours=24,this.ptz=!0,this.visible=!1,this.streamReady=!1,this.liveShowing=!1,this.paused=!1,this.speed=1}connectedCallback(){super.connectedCallback(),this.observer=new IntersectionObserver(([t])=>{this.visible=t.isIntersecting,this.visible&&!this.window&&this.load()},{rootMargin:"200px"}),this.observer.observe(this),this.refreshTimer=window.setInterval(()=>this.visible&&this.load(),6e4)}disconnectedCallback(){super.disconnectedCallback(),this.observer?.disconnect(),window.clearInterval(this.refreshTimer),window.clearInterval(this.livePoll)}willUpdate(t){if(t.has("hass")&&this.hass){const t=this.motionState;"on"===this.lastMotion&&"off"===t&&this.load(),this.lastMotion=t}var e;t.has("visible")&&this.visible&&!this.streamReady&&(e=this.entity,customElements.get("ha-camera-stream")?Promise.resolve():($t??($t=(async()=>{const t=await(window.loadCardHelpers?.()),i=await(t?.createCardElement({type:"picture-entity",entity:e,camera_view:"live"}));i?.remove?.(),await customElements.whenDefined("ha-camera-stream")})()),$t)).then(()=>this.streamReady=!0)}updated(){const t=this.renderRoot.querySelector("ha-camera-stream");if(!t)return this.liveShowing=!1,window.clearInterval(this.livePoll),void(this.livePoll=void 0);this.liveShowing||this.livePoll||(this.livePoll=window.setInterval(()=>{(function(t){const e=[t];for(;e.length;){const t=e.pop();if(t instanceof HTMLVideoElement&&t.readyState>=2&&t.videoWidth>0)return!0;t instanceof Element&&t.shadowRoot&&e.push(t.shadowRoot),e.push(...Array.from(t.children))}return!1})(t)&&(this.liveShowing=!0,window.clearInterval(this.livePoll),this.livePoll=void 0)},300))}get stateObj(){return this.hass?.states[this.entity]}get motionState(){const t=function(t,e){const i=t.entities?.[e]?.device_id;if(i)return Object.values(t.entities).find(t=>t.device_id===i&&t.platform===gt&&t.entity_id.startsWith("binary_sensor.")&&"motion"===t.translation_key)?.entity_id}(this.hass,this.entity);return t?this.hass.states[t]?.state:void 0}get clock(){return new wt(this.hass)}async load(){try{this.window=await this.hass.callWS({type:"zoneminder/events",entity_id:this.entity,hours:this.hours}),this.error=void 0}catch(t){this.error=t?.message??String(t)}}get span(){const t=Date.now();return{start:t-36e5*this.hours,end:t}}get clips(){return this.window?(t=this.window.events,e=Date.now(),t.map(t=>{const i=Date.parse(t.start),s=t.end?Date.parse(t.end):t.in_progress?e:i+1e3*t.length;return{event:t,start:i,end:Math.max(s,i+1e3)}})):[];var t,e}clipAt(t){return this.clips.find(e=>e.start<=t&&t<e.end&&e.event.video)}clipFrom(t){return this.clipAt(t)??this.clips.find(e=>e.start>t&&e.event.video)}play(t){const e=this.clipFrom(t);if(!e)return;const i=Math.max(t,e.start),s=this.playing?.clip.event.id===e.event.id;this.playing={clip:e,at:i},this.paused=!1;const r=(i-e.start)/1e3;s&&this.recordingVideo?(this.recordingVideo.currentTime=r,this.recordingVideo.play()):this.seekOnLoad=r}backToLive(){this.playing=void 0,this.paused=!1}onLoaded(t){const e=t.target;void 0!==this.seekOnLoad&&(e.currentTime=this.seekOnLoad),this.seekOnLoad=void 0,e.playbackRate=this.speed,e.play().catch(()=>this.paused=!0)}onTimeUpdate(t){if(!this.playing)return;const e=t.target;this.playing={...this.playing,at:this.playing.clip.start+1e3*e.currentTime}}onEnded(){if(!this.playing)return;const t=this.clips.find(t=>t.start>=this.playing.clip.end-ft&&t.event.id!==this.playing.clip.event.id&&t.event.video);t&&t.start-this.playing.clip.end<=ft?(this.playing={clip:t,at:t.start},this.seekOnLoad=0):this.paused=!0}togglePause(){const t=this.recordingVideo;t&&(t.paused?(t.play(),this.paused=!1):(t.pause(),this.paused=!0))}cycleSpeed(){this.speed=vt[(vt.indexOf(this.speed)+1)%vt.length],this.recordingVideo&&(this.recordingVideo.playbackRate=this.speed)}timeAt(t){const e=t.currentTarget.getBoundingClientRect(),i=Math.min(Math.max(t.clientX-e.left,0),e.width),{start:s,end:r}=this.span;return{t:s+i/e.width*(r-s),x:i}}onStripMove(t){const{t:e,x:i}=this.timeAt(t);this.hover={t:e,x:i,clip:this.clipAt(e)}}onStripClick(t){this.play(this.timeAt(t).t)}onStripKey(t){const{start:e,end:i}=this.span,s=6e4*(t.shiftKey?10:1),r=this.cursor??this.playing?.at??i;let o;switch(t.key){case"ArrowLeft":o=r-s;break;case"ArrowRight":o=r+s;break;case"Home":o=e;break;case"End":o=i;break;case"Enter":case" ":return t.preventDefault(),void this.play(r);case"Escape":return void this.backToLive();default:return}t.preventDefault(),this.cursor=Math.min(Math.max(o,e),i)}ptzCommand(t){this.hass.callService(gt,"ptz",{entity_id:this.entity,command:t})}ptzButton(t,e,i){const s=e=>{e.preventDefault(),this.ptzCommand(t)},r=()=>"home"!==t&&this.ptzCommand("stop");return q`<button
      class="ptz-${t}"
      aria-label=${i}
      @pointerdown=${s}
      @pointerup=${r}
      @pointerleave=${t=>t.buttons&&r()}
      @keydown=${t=>("Enter"===t.key||" "===t.key)&&!t.repeat&&s(t)}
      @keyup=${t=>("Enter"===t.key||" "===t.key)&&r()}
    >
      <ha-icon icon=${e}></ha-icon>
    </button>`}moreInfo(){this.dispatchEvent(new CustomEvent("hass-more-info",{detail:{entityId:this.entity},bubbles:!0,composed:!0}))}render(){const t=this.stateObj;if(!t)return q`<div class="missing">
        ${this.entity} isn't available. Check that the ZoneMinder integration is
        loaded.
      </div>`;const e=t.attributes,i=Number(e.orientation_degrees)||0,s=90===i||270===i,r=Number(e.width)||16,o=Number(e.height)||9,n=s?`${o} / ${r}`:`${r} / ${o}`,a="on"===this.motionState,h="unavailable"===t.state;return q`
      <figure class="tile ${a?"motion":""}" style="--ratio:${n}">
        <div
          class="frame"
          @click=${this.playing?this.togglePause:this.moreInfo}
        >
          ${e.entity_picture?q`<img class="still" alt="" src=${e.entity_picture} />`:F}
          <div
            class="turn ${this.liveShowing||this.playing?"":"waiting"}"
            style="--deg:${i}deg"
            ?data-sideways=${s}
          >
            ${!this.playing&&this.visible&&this.streamReady&&!h?q`<ha-camera-stream
                  .hass=${this.hass}
                  .stateObj=${t}
                  .muted=${!0}
                  .controls=${!1}
                  .allowExoPlayer=${!0}
                  .fitMode=${"cover"}
                ></ha-camera-stream>`:F}
          </div>
          ${this.playing?q`<video
                class="playback"
                muted
                playsinline
                preload="auto"
                poster=${this.playing.clip.event.thumbnail??F}
                src=${this.playing.clip.event.video}
                @loadedmetadata=${this.onLoaded}
                @timeupdate=${this.onTimeUpdate}
                @ended=${this.onEnded}
              ></video>`:F}
          ${this.renderPlate(t,a,h)}
          ${!this.playing&&this.ptz&&e.controllable?this.renderPtz():F}
        </div>
        ${this.playing?q`<div class="transport">
              <button @click=${this.togglePause}>
                ${this.paused?"Play":"Pause"}
              </button>
              <button
                @click=${this.cycleSpeed}
                aria-label="Playback speed, now ${this.speed} times"
              >
                ${this.speed}×
              </button>
              <button class="live-btn" @click=${this.backToLive}>
                Back to live
              </button>
            </div>`:F}
        ${this.renderStrip()}
      </figure>
    `}renderPlate(t,e,i){const s=this.label??bt(t);if(this.playing)return q`<figcaption class="plate">
        <span class="name">${s}</span>
        <span class="when">${this.clock.formatMoment(this.playing.at)}</span>
      </figcaption>`;const r=i?"Offline":e?"Motion":t.attributes.recording&&"None"!==t.attributes.recording?"Recording":"Live";return q`<figcaption class="plate">
      <span class="name">${s}</span>
      <span class="status ${r.toLowerCase()}">${r}</span>
    </figcaption>`}renderPtz(){return q`<div class="ptz" @click=${t=>t.stopPropagation()}>
      ${this.ptzButton("up","mdi:chevron-up","Tilt up")}
      ${this.ptzButton("left","mdi:chevron-left","Pan left")}
      ${this.ptzButton("home","mdi:crosshairs","Go to home position")}
      ${this.ptzButton("right","mdi:chevron-right","Pan right")}
      ${this.ptzButton("down","mdi:chevron-down","Tilt down")}
    </div>`}renderStrip(){const{start:t,end:e}=this.span,i=e-t,s=s=>(Math.min(Math.max(s,t),e)-t)/i*1e3,r=this.clips,o=function(t){const e=[];for(const i of t){const t=e[e.length-1];t&&i.start-t.end<=ft?t.end=Math.max(t.end,i.end):e.push({start:i.start,end:i.end})}return e}(r),n=r.filter(t=>t.event.alarm_frames>0),a=this.clock,h=a.ticks(t,e),l=this.playing?.at??this.cursor,c=this.hover?.clip;let d;this.error?d=`Couldn't load recordings: ${this.error}`:this.window&&0===r.length&&(d=`No recordings in the last ${this.hours} hours`);const p=void 0!==l?`${a.formatMoment(l)}${this.clipAt(l)?"":", no recording"}`:"Live";return q`
      <div class="strip-wrap">
        <div
          class="strip"
          role="slider"
          tabindex="0"
          aria-label="Recordings, last ${this.hours} hours"
          aria-valuemin=${t}
          aria-valuemax=${e}
          aria-valuenow=${l??e}
          aria-valuetext=${p}
          @pointermove=${this.onStripMove}
          @pointerleave=${()=>this.hover=void 0}
          @click=${this.onStripClick}
          @keydown=${this.onStripKey}
          @blur=${()=>this.cursor=void 0}
        >
          <svg
            viewBox="0 0 1000 40"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            ${h.map(t=>W`<line class="tick ${t.midnight?"midnight":""}" x1=${s(t.t)} x2=${s(t.t)} y1="0" y2="40" />`)}
            ${o.map(t=>W`<rect class="band" x=${s(t.start)} width=${Math.max(s(t.end)-s(t.start),1.5)} y="22" height="12" />`)}
            ${n.map(t=>{const e=6+.16*Math.min(t.event.max_score,100);return W`<rect class="alarm" x=${s(t.start)} width=${Math.max(s(t.end)-s(t.start),2.5)} y=${22-e} height=${e} />`})}
            ${c?W`<rect class="hover-clip" x=${s(c.start)} width=${Math.max(s(c.end)-s(c.start),1.5)} y="22" height="12" />`:F}
            ${void 0!==l?W`<line class="marker" x1=${s(l)} x2=${s(l)} y1="4" y2="40" />`:F}
            <rect class="now" x="996" width="4" y="18" height="20" />
          </svg>
          ${this.hover?this.renderPeek(this.hover):F}
        </div>
        <div class="ticks" aria-hidden="true">
          ${h.filter(t=>s(t.t)>30&&s(t.t)<900).map(t=>q`<span
                  style="left:${s(t.t)/10}%"
                  class=${t.midnight?"midnight":""}
                  >${t.label}</span
                >`)}
          <span class="now-label">Now</span>
        </div>
        ${d?q`<p class="empty">${d}</p>`:F}
      </div>
    `}renderPeek(t){const e=t.clip;return q`<div class="peek" style="--x:${t.x}px">
      ${e?.event.thumbnail?q`<img alt="" src=${e.event.thumbnail} />`:F}
      <span>${this.clock.formatMoment(t.t)}</span>
      ${e?F:q`<span class="gap">No recording</span>`}
      ${e&&e.event.alarm_frames>0?q`<span class="cause"
            >${e.event.notes?.trim()||e.event.cause}</span
          >`:F}
    </div>`}}At.styles=[_t,n`
      :host {
        display: block;
        min-width: 0;
      }

      .tile {
        margin: 0;
        display: flex;
        flex-direction: column;
        background: var(--zm-kerb);
        border-radius: 10px;
        overflow: hidden;
        height: 100%;
      }

      .frame {
        position: relative;
        width: 100%;
        aspect-ratio: var(--ratio);
        /* Tall cameras would fill a phone screen on their own. */
        max-height: 70vh;
        background: #000;
        overflow: hidden;
        container-type: size;
        cursor: pointer;
      }

      .turn.waiting {
        opacity: 0;
      }
      .turn {
        position: absolute;
        inset: 0;
      }
      .turn[data-sideways] {
        inset: auto;
        left: 50%;
        top: 50%;
        width: 100cqh;
        height: 100cqw;
        transform: translate(-50%, -50%) rotate(var(--deg));
      }
      .turn:not([data-sideways]) {
        transform: rotate(var(--deg));
      }

      .still,
      .playback {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      .turn > * {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
      }
      ha-camera-stream {
        --video-max-height: 100%;
      }

      /* The name plate sits on the picture like a caption on a monitor wall. */
      .plate {
        position: absolute;
        inset: auto 0 0 0;
        display: flex;
        align-items: baseline;
        gap: 12px;
        padding: 28px 14px 10px;
        background: linear-gradient(
          to top,
          rgba(10, 14, 17, 0.82),
          rgba(10, 14, 17, 0)
        );
        color: var(--zm-fog);
        font-family: var(--zm-font);
        pointer-events: none;
      }
      .plate > * {
        pointer-events: auto;
      }
      .name {
        font-size: 1.125rem;
        font-weight: 600;
        letter-spacing: 0.01em;
        flex: 1;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .status,
      .when {
        font-size: 0.9375rem;
        font-variant-numeric: tabular-nums;
        color: var(--zm-concrete);
      }
      .status.motion {
        color: var(--zm-sodium);
        font-weight: 600;
      }
      .status.offline {
        color: var(--zm-fog);
      }
      .when {
        color: var(--zm-fog);
      }
      .tile.motion .plate {
        box-shadow: inset 4px 0 0 var(--zm-sodium);
      }

      .transport {
        display: flex;
        gap: 8px;
        padding: 10px 14px 0;
      }
      .transport .live-btn {
        margin-left: auto;
      }
      button {
        font: 500 0.9375rem/1 var(--zm-font);
        color: var(--zm-fog);
        background: transparent;
        border: 1px solid rgba(227, 231, 233, 0.22);
        border-radius: 6px;
        padding: 8px 14px;
        min-height: 36px;
        cursor: pointer;
      }
      button:hover {
        border-color: rgba(227, 231, 233, 0.45);
      }
      .live-btn {
        background: var(--zm-fog);
        color: var(--zm-asphalt);
        border-color: var(--zm-fog);
      }
      :focus-visible {
        outline: 2px solid var(--zm-sodium);
        outline-offset: 2px;
      }

      .ptz {
        position: absolute;
        top: 10px;
        right: 10px;
        display: grid;
        grid-template-areas: ". up ." "left home right" ". down .";
        gap: 2px;
        opacity: 0;
        transition: opacity 120ms;
      }
      .frame:hover .ptz,
      .ptz:focus-within {
        opacity: 1;
      }
      .ptz button {
        background: rgba(24, 32, 38, 0.8);
        min-height: 0;
        width: 34px;
        height: 34px;
        padding: 0;
        display: grid;
        place-items: center;
        --mdc-icon-size: 20px;
      }
      .ptz-up {
        grid-area: up;
      }
      .ptz-down {
        grid-area: down;
      }
      .ptz-left {
        grid-area: left;
      }
      .ptz-right {
        grid-area: right;
      }
      .ptz-home {
        grid-area: home;
      }

      /* The strip: what this camera saw over the last day. */
      .strip-wrap {
        position: relative;
        padding: 10px 14px 12px;
        font-family: var(--zm-font);
      }
      .strip {
        position: relative;
        height: 40px;
        cursor: crosshair;
        border-radius: 4px;
        touch-action: none;
      }
      .strip svg {
        width: 100%;
        height: 100%;
        display: block;
        overflow: visible;
      }
      .tick {
        stroke: rgba(126, 136, 144, 0.28);
        stroke-width: 1;
        vector-effect: non-scaling-stroke;
      }
      .tick.midnight {
        stroke: rgba(126, 136, 144, 0.6);
      }
      .band {
        fill: var(--zm-tape);
      }
      .hover-clip {
        fill: #5d8fae;
      }
      .alarm {
        fill: var(--zm-sodium);
      }
      .marker {
        stroke: var(--zm-sodium);
        stroke-width: 2;
        vector-effect: non-scaling-stroke;
      }
      .now {
        fill: var(--zm-concrete);
      }
      .tile.motion .now {
        fill: var(--zm-sodium);
        animation: breathe 1.6s ease-in-out infinite;
      }
      @keyframes breathe {
        50% {
          opacity: 0.35;
        }
      }

      .ticks {
        position: relative;
        height: 16px;
        margin-top: 4px;
        font-size: 0.8125rem;
        color: var(--zm-concrete);
        font-variant-numeric: tabular-nums;
      }
      .ticks span {
        position: absolute;
        transform: translateX(-50%);
        white-space: nowrap;
      }
      .ticks span.midnight {
        color: var(--zm-fog);
      }
      .ticks .now-label {
        right: 0;
        transform: none;
      }

      .peek {
        position: absolute;
        bottom: calc(100% + 8px);
        left: clamp(80px, var(--x), calc(100% - 80px));
        transform: translateX(-50%);
        width: 160px;
        display: flex;
        flex-direction: column;
        gap: 2px;
        padding: 4px 4px 6px;
        background: var(--zm-asphalt);
        border: 1px solid rgba(227, 231, 233, 0.16);
        border-radius: 6px;
        color: var(--zm-fog);
        font-size: 0.875rem;
        font-variant-numeric: tabular-nums;
        pointer-events: none;
        z-index: 2;
      }
      .peek img {
        width: 100%;
        aspect-ratio: var(--ratio);
        max-height: 180px;
        object-fit: cover;
        border-radius: 3px;
        background: #000;
      }
      .peek span {
        padding: 0 4px;
      }
      .peek .gap,
      .peek .cause {
        color: var(--zm-concrete);
      }
      .peek .cause {
        color: var(--zm-sodium);
      }

      .empty {
        margin: 6px 0 0;
        color: var(--zm-concrete);
        font-size: 0.875rem;
      }
      .missing {
        padding: 16px;
        color: var(--zm-concrete);
        font-family: var(--zm-font);
      }

      @media (prefers-reduced-motion: reduce) {
        .tile.motion .now {
          animation: none;
        }
        .ptz {
          transition: none;
        }
      }
    `],t([ut({attribute:!1})],At.prototype,"hass",void 0),t([ut()],At.prototype,"entity",void 0),t([ut()],At.prototype,"label",void 0),t([ut({type:Number})],At.prototype,"hours",void 0),t([ut({type:Boolean})],At.prototype,"ptz",void 0),t([mt()],At.prototype,"visible",void 0),t([mt()],At.prototype,"streamReady",void 0),t([mt()],At.prototype,"liveShowing",void 0),t([mt()],At.prototype,"window",void 0),t([mt()],At.prototype,"error",void 0),t([mt()],At.prototype,"playing",void 0),t([mt()],At.prototype,"paused",void 0),t([mt()],At.prototype,"speed",void 0),t([mt()],At.prototype,"hover",void 0),t([mt()],At.prototype,"cursor",void 0),t([
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function(t){return(e,i,s)=>((t,e,i)=>(i.configurable=!0,i.enumerable=!0,Reflect.decorate&&"object"!=typeof e&&Object.defineProperty(t,e,i),i))(e,i,{get(){return(e=>e.renderRoot?.querySelector(t)??null)(this)}})}("video.playback")],At.prototype,"recordingVideo",void 0);class xt extends lt{static getStubConfig(){return{}}setConfig(t){if(void 0!==t.hours&&(t.hours<1||t.hours>168))throw new Error("hours must be between 1 and 168");this.config=t,function(){if(yt)return;yt=!0;const t=document.createElement("link");t.rel="stylesheet",t.href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@400;500;600&display=swap",document.head.appendChild(t)}()}getCardSize(){return 6*Math.ceil(this.cameras.length/(this.config?.columns??2))}getGridOptions(){return{columns:"full",rows:"auto"}}get cameras(){return this.hass?this.config?.entities?.length?this.config.entities.map(t=>"string"==typeof t?{entity:t}:t):(t=this.hass,Object.values(t.entities??{}).filter(t=>t.platform===gt&&t.entity_id.startsWith("camera.")).map(t=>t.entity_id).filter(e=>t.states[e]).sort((e,i)=>bt(t.states[e]).localeCompare(bt(t.states[i])))).map(t=>({entity:t})):[];var t}render(){const t=this.cameras,e=this.config.columns;return q`
      <ha-card>
        ${t.length?q`<div
              class="wall"
              style=${e?`grid-template-columns: repeat(${e}, minmax(0, 1fr))`:""}
            >
              ${t.map(t=>q`<zm-camera-tile
                    .hass=${this.hass}
                    .entity=${t.entity}
                    .label=${t.name}
                    .hours=${this.config.hours??24}
                    .ptz=${this.config.ptz??!0}
                    class=${this.isSideways(t.entity)?"tall":""}
                  ></zm-camera-tile>`)}
            </div>`:q`<p class="none">
              No ZoneMinder cameras yet. Add the ZoneMinder integration under
              Settings, then Devices & services.
            </p>`}
      </ha-card>
    `}isSideways(t){const e=Number(this.hass.states[t]?.attributes.orientation_degrees)||0;return 90===e||270===e}}xt.styles=[_t,n`
      ha-card {
        background: var(--zm-asphalt);
        padding: 12px;
        border-radius: var(--ha-card-border-radius, 12px);
        overflow: visible;
      }
      .wall {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(min(340px, 100%), 1fr));
        grid-auto-flow: row dense;
        gap: 12px;
        align-items: start;
      }
      .none {
        margin: 0;
        padding: 8px 4px;
        color: var(--zm-fog);
        font-family: var(--zm-font);
      }
    `],t([ut({attribute:!1})],xt.prototype,"hass",void 0),t([mt()],xt.prototype,"config",void 0),customElements.get("zoneminder-card")||(customElements.define("zm-camera-tile",At),customElements.define("zoneminder-card",xt),window.customCards=window.customCards||[],window.customCards.push({type:"zoneminder-card",name:"ZoneMinder",description:"Live cameras with a day of recordings under each one. Click the strip to play back.",preview:!0}));export{At as ZmCameraTile,xt as ZoneMinderCard};
