function t(t,e,i,s){var r,o=arguments.length,n=o<3?e:null===s?s=Object.getOwnPropertyDescriptor(e,i):s;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)n=Reflect.decorate(t,e,i,s);else for(var a=t.length-1;a>=0;a--)(r=t[a])&&(n=(o<3?r(n):o>3?r(e,i,n):r(e,i))||n);return o>3&&n&&Object.defineProperty(e,i,n),n}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const e=globalThis,i=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,s=Symbol(),r=new WeakMap;let o=class{constructor(t,e,i){if(this._$cssResult$=!0,i!==s)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(i&&void 0===t){const i=void 0!==e&&1===e.length;i&&(t=r.get(e)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),i&&r.set(e,t))}return t}toString(){return this.cssText}};const n=(t,...e)=>{const i=1===t.length?t[0]:e.reduce((e,i,s)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+t[s+1],t[0]);return new o(i,t,s)},a=i?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const i of t.cssRules)e+=i.cssText;return(t=>new o("string"==typeof t?t:t+"",void 0,s))(e)})(t):t,{is:d,defineProperty:c,getOwnPropertyDescriptor:h,getOwnPropertyNames:l,getOwnPropertySymbols:p,getPrototypeOf:u}=Object,_=globalThis,g=_.trustedTypes,f=g?g.emptyScript:"",m=_.reactiveElementPolyfillSupport,v=(t,e)=>t,$={toAttribute(t,e){switch(e){case Boolean:t=t?f:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let i=t;switch(e){case Boolean:i=null!==t;break;case Number:i=null===t?null:Number(t);break;case Object:case Array:try{i=JSON.parse(t)}catch(t){i=null}}return i}},y=(t,e)=>!d(t,e),b={attribute:!0,type:String,converter:$,reflect:!1,useDefault:!1,hasChanged:y};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),_.litPropertyMetadata??=new WeakMap;let A=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=b){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const i=Symbol(),s=this.getPropertyDescriptor(t,i,e);void 0!==s&&c(this.prototype,t,s)}}static getPropertyDescriptor(t,e,i){const{get:s,set:r}=h(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:s,set(e){const o=s?.call(this);r?.call(this,e),this.requestUpdate(t,o,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??b}static _$Ei(){if(this.hasOwnProperty(v("elementProperties")))return;const t=u(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(v("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(v("properties"))){const t=this.properties,e=[...l(t),...p(t)];for(const i of e)this.createProperty(i,t[i])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,i]of e)this.elementProperties.set(t,i)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const i=this._$Eu(t,e);void 0!==i&&this._$Eh.set(i,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const i=new Set(t.flat(1/0).reverse());for(const t of i)e.unshift(a(t))}else void 0!==t&&e.push(a(t));return e}static _$Eu(t,e){const i=e.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const i of e.keys())this.hasOwnProperty(i)&&(t.set(i,this[i]),delete this[i]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((t,s)=>{if(i)t.adoptedStyleSheets=s.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const i of s){const s=document.createElement("style"),r=e.litNonce;void 0!==r&&s.setAttribute("nonce",r),s.textContent=i.cssText,t.appendChild(s)}})(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,i){this._$AK(t,i)}_$ET(t,e){const i=this.constructor.elementProperties.get(t),s=this.constructor._$Eu(t,i);if(void 0!==s&&!0===i.reflect){const r=(void 0!==i.converter?.toAttribute?i.converter:$).toAttribute(e,i.type);this._$Em=t,null==r?this.removeAttribute(s):this.setAttribute(s,r),this._$Em=null}}_$AK(t,e){const i=this.constructor,s=i._$Eh.get(t);if(void 0!==s&&this._$Em!==s){const t=i.getPropertyOptions(s),r="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:$;this._$Em=s;const o=r.fromAttribute(e,t.type);this[s]=o??this._$Ej?.get(s)??o,this._$Em=null}}requestUpdate(t,e,i,s=!1,r){if(void 0!==t){const o=this.constructor;if(!1===s&&(r=this[t]),i??=o.getPropertyOptions(t),!((i.hasChanged??y)(r,e)||i.useDefault&&i.reflect&&r===this._$Ej?.get(t)&&!this.hasAttribute(o._$Eu(t,i))))return;this.C(t,e,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:i,reflect:s,wrapped:r},o){i&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,o??e??this[t]),!0!==r||void 0!==o)||(this._$AL.has(t)||(this.hasUpdated||i||(e=void 0),this._$AL.set(t,e)),!0===s&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,i]of t){const{wrapped:t}=i,s=this[e];!0!==t||this._$AL.has(e)||void 0===s||this.C(e,void 0,i,s)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};A.elementStyles=[],A.shadowRootOptions={mode:"open"},A[v("elementProperties")]=new Map,A[v("finalized")]=new Map,m?.({ReactiveElement:A}),(_.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const w=globalThis,E=t=>t,S=w.trustedTypes,x=S?S.createPolicy("lit-html",{createHTML:t=>t}):void 0,C="$lit$",T=`lit$${Math.random().toFixed(9).slice(2)}$`,O="?"+T,M=`<${O}>`,R=document,P=()=>R.createComment(""),U=t=>null===t||"object"!=typeof t&&"function"!=typeof t,k=Array.isArray,D="[ \t\n\f\r]",I=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,N=/-->/g,H=/>/g,z=RegExp(`>|${D}(?:([^\\s"'>=/]+)(${D}*=${D}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),L=/'/g,j=/"/g,W=/^(?:script|style|textarea|title)$/i,q=(t=>(e,...i)=>({_$litType$:t,strings:e,values:i}))(1),B=Symbol.for("lit-noChange"),F=Symbol.for("lit-nothing"),V=new WeakMap,J=R.createTreeWalker(R,129);function G(t,e){if(!k(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==x?x.createHTML(e):e}const K=(t,e)=>{const i=t.length-1,s=[];let r,o=2===e?"<svg>":3===e?"<math>":"",n=I;for(let e=0;e<i;e++){const i=t[e];let a,d,c=-1,h=0;for(;h<i.length&&(n.lastIndex=h,d=n.exec(i),null!==d);)h=n.lastIndex,n===I?"!--"===d[1]?n=N:void 0!==d[1]?n=H:void 0!==d[2]?(W.test(d[2])&&(r=RegExp("</"+d[2],"g")),n=z):void 0!==d[3]&&(n=z):n===z?">"===d[0]?(n=r??I,c=-1):void 0===d[1]?c=-2:(c=n.lastIndex-d[2].length,a=d[1],n=void 0===d[3]?z:'"'===d[3]?j:L):n===j||n===L?n=z:n===N||n===H?n=I:(n=z,r=void 0);const l=n===z&&t[e+1].startsWith("/>")?" ":"";o+=n===I?i+M:c>=0?(s.push(a),i.slice(0,c)+C+i.slice(c)+T+l):i+T+(-2===c?e:l)}return[G(t,o+(t[i]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),s]};class Z{constructor({strings:t,_$litType$:e},i){let s;this.parts=[];let r=0,o=0;const n=t.length-1,a=this.parts,[d,c]=K(t,e);if(this.el=Z.createElement(d,i),J.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(s=J.nextNode())&&a.length<n;){if(1===s.nodeType){if(s.hasAttributes())for(const t of s.getAttributeNames())if(t.endsWith(C)){const e=c[o++],i=s.getAttribute(t).split(T),n=/([.?@])?(.*)/.exec(e);a.push({type:1,index:r,name:n[2],strings:i,ctor:"."===n[1]?et:"?"===n[1]?it:"@"===n[1]?st:tt}),s.removeAttribute(t)}else t.startsWith(T)&&(a.push({type:6,index:r}),s.removeAttribute(t));if(W.test(s.tagName)){const t=s.textContent.split(T),e=t.length-1;if(e>0){s.textContent=S?S.emptyScript:"";for(let i=0;i<e;i++)s.append(t[i],P()),J.nextNode(),a.push({type:2,index:++r});s.append(t[e],P())}}}else if(8===s.nodeType)if(s.data===O)a.push({type:2,index:r});else{let t=-1;for(;-1!==(t=s.data.indexOf(T,t+1));)a.push({type:7,index:r}),t+=T.length-1}r++}}static createElement(t,e){const i=R.createElement("template");return i.innerHTML=t,i}}function Y(t,e,i=t,s){if(e===B)return e;let r=void 0!==s?i._$Co?.[s]:i._$Cl;const o=U(e)?void 0:e._$litDirective$;return r?.constructor!==o&&(r?._$AO?.(!1),void 0===o?r=void 0:(r=new o(t),r._$AT(t,i,s)),void 0!==s?(i._$Co??=[])[s]=r:i._$Cl=r),void 0!==r&&(e=Y(t,r._$AS(t,e.values),r,s)),e}class Q{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:i}=this._$AD,s=(t?.creationScope??R).importNode(e,!0);J.currentNode=s;let r=J.nextNode(),o=0,n=0,a=i[0];for(;void 0!==a;){if(o===a.index){let e;2===a.type?e=new X(r,r.nextSibling,this,t):1===a.type?e=new a.ctor(r,a.name,a.strings,this,t):6===a.type&&(e=new rt(r,this,t)),this._$AV.push(e),a=i[++n]}o!==a?.index&&(r=J.nextNode(),o++)}return J.currentNode=R,s}p(t){let e=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(t,i,e),e+=i.strings.length-2):i._$AI(t[e])),e++}}class X{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,i,s){this.type=2,this._$AH=F,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=i,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=Y(this,t,e),U(t)?t===F||null==t||""===t?(this._$AH!==F&&this._$AR(),this._$AH=F):t!==this._$AH&&t!==B&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>k(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==F&&U(this._$AH)?this._$AA.nextSibling.data=t:this.T(R.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:i}=t,s="number"==typeof i?this._$AC(t):(void 0===i.el&&(i.el=Z.createElement(G(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===s)this._$AH.p(e);else{const t=new Q(s,this),i=t.u(this.options);t.p(e),this.T(i),this._$AH=t}}_$AC(t){let e=V.get(t.strings);return void 0===e&&V.set(t.strings,e=new Z(t)),e}k(t){k(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let i,s=0;for(const r of t)s===e.length?e.push(i=new X(this.O(P()),this.O(P()),this,this.options)):i=e[s],i._$AI(r),s++;s<e.length&&(this._$AR(i&&i._$AB.nextSibling,s),e.length=s)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=E(t).nextSibling;E(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class tt{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,i,s,r){this.type=1,this._$AH=F,this._$AN=void 0,this.element=t,this.name=e,this._$AM=s,this.options=r,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=F}_$AI(t,e=this,i,s){const r=this.strings;let o=!1;if(void 0===r)t=Y(this,t,e,0),o=!U(t)||t!==this._$AH&&t!==B,o&&(this._$AH=t);else{const s=t;let n,a;for(t=r[0],n=0;n<r.length-1;n++)a=Y(this,s[i+n],e,n),a===B&&(a=this._$AH[n]),o||=!U(a)||a!==this._$AH[n],a===F?t=F:t!==F&&(t+=(a??"")+r[n+1]),this._$AH[n]=a}o&&!s&&this.j(t)}j(t){t===F?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class et extends tt{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===F?void 0:t}}class it extends tt{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==F)}}class st extends tt{constructor(t,e,i,s,r){super(t,e,i,s,r),this.type=5}_$AI(t,e=this){if((t=Y(this,t,e,0)??F)===B)return;const i=this._$AH,s=t===F&&i!==F||t.capture!==i.capture||t.once!==i.once||t.passive!==i.passive,r=t!==F&&(i===F||s);s&&this.element.removeEventListener(this.name,this,i),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class rt{constructor(t,e,i){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(t){Y(this,t)}}const ot=w.litHtmlPolyfillSupport;ot?.(Z,X),(w.litHtmlVersions??=[]).push("3.3.2");const nt=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class at extends A{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,i)=>{const s=i?.renderBefore??e;let r=s._$litPart$;if(void 0===r){const t=i?.renderBefore??null;s._$litPart$=r=new X(e.insertBefore(P(),t),t,void 0,i??{})}return r._$AI(t),r})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return B}}at._$litElement$=!0,at.finalized=!0,nt.litElementHydrateSupport?.({LitElement:at});const dt=nt.litElementPolyfillSupport;dt?.({LitElement:at}),(nt.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const ct=t=>(e,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)},ht={attribute:!0,type:String,converter:$,reflect:!1,hasChanged:y},lt=(t=ht,e,i)=>{const{kind:s,metadata:r}=i;let o=globalThis.litPropertyMetadata.get(r);if(void 0===o&&globalThis.litPropertyMetadata.set(r,o=new Map),"setter"===s&&((t=Object.create(t)).wrapped=!0),o.set(i.name,t),"accessor"===s){const{name:s}=i;return{set(i){const r=e.get.call(this);e.set.call(this,i),this.requestUpdate(s,r,t,!0,i)},init(e){return void 0!==e&&this.C(s,void 0,t,e),e}}}if("setter"===s){const{name:s}=i;return function(i){const r=this[s];e.call(this,i),this.requestUpdate(s,r,t,!0,i)}}throw Error("Unsupported decorator location: "+s)};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function pt(t){return(e,i)=>"object"==typeof i?lt(t,e,i):((t,e,i)=>{const s=e.hasOwnProperty(i);return e.constructor.createProperty(i,t),s?Object.getOwnPropertyDescriptor(e,i):void 0})(t,e,i)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ut(t){return pt({...t,state:!0,attribute:!1})}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */let _t=class extends at{constructor(){super(...arguments),this.go2rtcUrl="",this.streamId="",this.mode="webrtc",this.orientation="ROTATE_0",this.videoWidth=0,this.videoHeight=0,this.autoplay=!0,this.muted=!0,this._connected=!1,this._error=null}render(){const t=this._getOrientationClass(),e=this._getVideoStyle();return q`
      <video
        class="${t}"
        style="${e}"
        ?autoplay=${this.autoplay}
        ?muted=${this.muted}
        playsinline
        @loadedmetadata=${this._handleVideoLoaded}
      ></video>
      ${this._connected||this._error?"":q`
            <div class="loading">
              <div class="spinner"></div>
              <div>Connecting...</div>
            </div>
          `}
      ${this._error?q`
            <div class="error">
              <div>Connection Error</div>
              <div style="font-size: 12px; margin-top: 8px;">${this._error}</div>
            </div>
          `:""}
    `}_getOrientationClass(){switch(this.orientation){case"ROTATE_90":return"rotate-90";case"ROTATE_180":return"rotate-180";case"ROTATE_270":return"rotate-270";default:return""}}_getVideoStyle(){if(("ROTATE_90"===this.orientation||"ROTATE_270"===this.orientation)&&this.videoWidth>0&&this.videoHeight>0){return`--video-scale: ${this.videoWidth/this.videoHeight}`}return""}updated(t){super.updated(t),(t.has("go2rtcUrl")||t.has("streamId")||t.has("mode"))&&this._reconnect()}disconnectedCallback(){super.disconnectedCallback(),this.disconnect()}async connect(){if(this.go2rtcUrl&&this.streamId)switch(this._error=null,this.mode){case"webrtc":await this._connectWebRTC();break;case"mse":this._connectMSE();break;case"hls":this._connectHLS();break;case"mjpeg":this._connectMJPEG()}else this._error="Missing go2rtc URL or stream ID"}disconnect(){this._ws&&(this._ws.close(),this._ws=void 0),this._pc&&(this._pc.close(),this._pc=void 0),this._video&&(this._video.srcObject=null,this._video.src=""),this._connected=!1}_reconnect(){this.disconnect(),this.connect()}async _connectWebRTC(){try{this._pc=new RTCPeerConnection({iceServers:[{urls:["stun:stun.cloudflare.com:3478"]},{urls:["stun:stun.l.google.com:19302"]}]}),this._pc.addTransceiver("video",{direction:"recvonly"}),this._pc.addTransceiver("audio",{direction:"recvonly"}),this._pc.ontrack=t=>{this._video&&(this._video.srcObject=t.streams[0],this._connected=!0)},this._pc.onconnectionstatechange=()=>{"failed"===this._pc?.connectionState&&(this._error="WebRTC connection failed",this.disconnect())};const t=this.go2rtcUrl.replace("http://","ws://").replace("https://","wss://")+`/api/ws?src=${this.streamId}`;this._ws=new WebSocket(t),this._ws.onopen=()=>{this._pc&&(this._pc.onicecandidate=t=>{if(t.candidate&&this._ws?.readyState===WebSocket.OPEN){const e={type:"webrtc/candidate",value:t.candidate.candidate};this._ws.send(JSON.stringify(e))}},this._pc.createOffer().then(t=>this._pc.setLocalDescription(t)).then(()=>{const t={type:"webrtc/offer",value:this._pc.localDescription.sdp};this._ws.send(JSON.stringify(t))}).catch(t=>{this._error=`Failed to create offer: ${t.message}`}))},this._ws.onmessage=t=>{const e=JSON.parse(t.data);"webrtc/candidate"===e.type&&this._pc?this._pc.addIceCandidate({candidate:e.value,sdpMid:"0"}).catch(t=>{console.warn("Failed to add ICE candidate:",t)}):"webrtc/answer"===e.type&&this._pc&&this._pc.setRemoteDescription({type:"answer",sdp:e.value}).catch(t=>{this._error=`Failed to set remote description: ${t.message}`})},this._ws.onerror=t=>{this._error="WebSocket connection failed",this.disconnect()},this._ws.onclose=()=>{this._connected&&setTimeout(()=>this._reconnect(),5e3)}}catch(t){this._error=`WebRTC error: ${t.message}`}}_connectMSE(){if(!this._video)return;const t=`${this.go2rtcUrl}/api/stream.mp4?src=${this.streamId}`;this._video.src=t,this._connected=!0}_connectHLS(){if(!this._video)return;const t=`${this.go2rtcUrl}/api/stream.m3u8?src=${this.streamId}`;this._video.src=t,this._connected=!0}_connectMJPEG(){if(!this._video)return;const t=`${this.go2rtcUrl}/api/stream.mjpeg?src=${this.streamId}`,e=new Image;e.src=t,e.onload=()=>{this._connected=!0},e.onerror=()=>{this._error="Failed to load MJPEG stream"},this._video.poster=t}_handleVideoLoaded(){this._connected=!0}};_t.styles=n`
    :host {
      display: block;
      position: relative;
      width: 100%;
      height: 100%;
      background: #000;
      overflow: hidden;
    }

    video {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      object-fit: contain;
      transform-origin: center center;
    }

    /*
     * For 90° and 270° rotations, we need to scale the video to compensate
     * for letterboxing. The scale factor equals the video's aspect ratio.
     * This is applied via inline style with CSS variable --video-scale.
     */
    video.rotate-90 {
      transform: rotate(90deg) scale(var(--video-scale, 1));
    }

    video.rotate-180 {
      transform: rotate(180deg);
    }

    video.rotate-270 {
      transform: rotate(270deg) scale(var(--video-scale, 1));
    }

    .error {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      color: #ff5252;
      background: rgba(0, 0, 0, 0.8);
      padding: 16px;
      border-radius: 4px;
      text-align: center;
      font-family: system-ui, -apple-system, sans-serif;
    }

    .loading {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      color: #fff;
      font-family: system-ui, -apple-system, sans-serif;
    }

    .spinner {
      border: 3px solid rgba(255, 255, 255, 0.3);
      border-top: 3px solid #fff;
      border-radius: 50%;
      width: 40px;
      height: 40px;
      animation: spin 1s linear infinite;
      margin: 0 auto 16px;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
  `,t([pt({type:String})],_t.prototype,"go2rtcUrl",void 0),t([pt({type:String})],_t.prototype,"streamId",void 0),t([pt({type:String})],_t.prototype,"mode",void 0),t([pt({type:String})],_t.prototype,"orientation",void 0),t([pt({type:Number})],_t.prototype,"videoWidth",void 0),t([pt({type:Number})],_t.prototype,"videoHeight",void 0),t([pt({type:Boolean})],_t.prototype,"autoplay",void 0),t([pt({type:Boolean})],_t.prototype,"muted",void 0),t([ut()],_t.prototype,"_connected",void 0),t([ut()],_t.prototype,"_error",void 0),t([
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function(t){return(e,i,s)=>((t,e,i)=>(i.configurable=!0,i.enumerable=!0,Reflect.decorate&&"object"!=typeof e&&Object.defineProperty(t,e,i),i))(e,i,{get(){return(e=>e.renderRoot?.querySelector(t)??null)(this)}})}("video")],_t.prototype,"_video",void 0),_t=t([ct("webrtc-player")],_t),window.customCards=window.customCards||[],window.customCards.push({type:"zoneminder-card",name:"ZoneMinder Card",description:"Display ZoneMinder cameras with direct go2rtc WebRTC streaming",preview:!1,documentationURL:"https://github.com/yourusername/zoneminder-card"});let gt=class extends at{constructor(){super(...arguments),this._go2rtcUrl="",this._editMode=!1,this._draggedIndex=null}setConfig(t){if(!t.monitors||0===t.monitors.length)throw new Error("You must specify at least one monitor");let e=t.monitors;const i=this._loadMonitorOrder(t.monitors);i&&(e=i),this._config={columns:4,aspect_ratio:"16:9",streaming_mode:"webrtc",show_motion_indicator:!0,show_controls:!1,refresh_interval:1e3,click_action:"fullscreen",...t,monitors:e}}_getStorageKey(t){const e=t.map(t=>t.entity).sort().join(",");return`zoneminder-card-order:${e}`}_loadMonitorOrder(t){try{const e=this._getStorageKey(t),i=localStorage.getItem(e);if(!i)return null;const s=JSON.parse(i),r=new Set(t.map(t=>t.entity)),o=new Set(s);if(r.size!==o.size)return null;for(const t of r)if(!o.has(t))return null;const n=new Map(t.map(t=>[t.entity,t]));return s.map(t=>n.get(t))}catch{return null}}_saveMonitorOrder(t){try{const e=this._getStorageKey(t),i=t.map(t=>t.entity);localStorage.setItem(e,JSON.stringify(i))}catch{}}getCardSize(){return 3*Math.ceil((this._config?.monitors?.length||1)/(this._config?.columns||2))}updated(t){super.updated(t),t.has("hass")&&this.hass&&this._detectGo2rtcUrl()}_isPortraitCamera(t){const e=t?.attributes?.orientation||"ROTATE_0",i=this._normalizeOrientation(e);return"ROTATE_90"===i||"ROTATE_270"===i}_getColumnSpan(t){if(t.columns)return t.columns;const e=this.hass?.states[t.entity];return e?this._isPortraitCamera(e)?1:2:1}render(){if(!this._config||!this.hass)return q``;if(!this._go2rtcUrl)return q`
        <div class="warning">
          <strong>Warning:</strong> go2rtc URL not configured or auto-detected.<br />
          Please configure <code>zoneminder_go2rtc_url</code> in card configuration.
        </div>
      `;const t=this._config.columns||4;return q`
      <div class="header-row">
        <div class="card-header" style="padding: 0; margin: 0;">
          ${this._config.title||""}
        </div>
        <button
          class="edit-toggle ${this._editMode?"active":""}"
          @click=${this._toggleEditMode}
        >
          ${this._editMode?"Done":"Edit Layout"}
        </button>
      </div>
      <div class="grid" style="grid-template-columns: repeat(${t}, 1fr)">
        ${this._config.monitors.map((t,e)=>this._renderMonitor(t,e))}
      </div>
    `}_toggleEditMode(){this._editMode=!this._editMode,this._editMode||(this._draggedIndex=null)}_renderMonitor(t,e){const i=this.hass.states[t.entity],s=this._getColumnSpan(t),r=this._draggedIndex===e;if(!i)return q`
        <div
          class="monitor ${this._editMode?"edit-mode":""}"
          style="grid-column: span ${s}; min-height: 100px"
          draggable=${this._editMode}
          @dragstart=${t=>this._handleDragStart(t,e)}
          @dragover=${t=>this._handleDragOver(t,e)}
          @dragleave=${t=>this._handleDragLeave(t)}
          @drop=${t=>this._handleDrop(t,e)}
          @dragend=${this._handleDragEnd}
        >
          <div class="error" style="margin: 0; height: 100%; display: flex; align-items: center; justify-content: center;">
            Entity ${t.entity} not found
          </div>
        </div>
      `;const o=Number(i.attributes.width)||0,n=Number(i.attributes.height)||0,a=i.attributes.orientation||"ROTATE_0",d=this._normalizeOrientation(a),c=this._isPortraitCamera(i),h=this._getAspectRatioCss(o,n,c),l=t.stream_id||i.attributes.go2rtc_stream_id||i.attributes.monitor_id;if(!l)return q`
        <div
          class="monitor ${this._editMode?"edit-mode":""}"
          style="grid-column: span ${s}; aspect-ratio: ${h}"
          draggable=${this._editMode}
          @dragstart=${t=>this._handleDragStart(t,e)}
          @dragover=${t=>this._handleDragOver(t,e)}
          @dragleave=${t=>this._handleDragLeave(t)}
          @drop=${t=>this._handleDrop(t,e)}
          @dragend=${this._handleDragEnd}
        >
          <div class="error" style="margin: 0; height: 100%; display: flex; align-items: center; justify-content: center;">
            No stream ID found for ${t.entity}
          </div>
        </div>
      `;const p=t.entity.replace("camera.","binary_sensor.")+"_motion",u=this.hass.states[p],_="on"===u?.state,g=t.name||i.attributes.friendly_name||t.entity,f=["monitor"];return _&&f.push("motion-active"),this._editMode&&f.push("edit-mode"),r&&f.push("dragging"),q`
      <div
        class=${f.join(" ")}
        style="grid-column: span ${s}; aspect-ratio: ${h}"
        draggable=${this._editMode}
        @dragstart=${t=>this._handleDragStart(t,e)}
        @dragover=${t=>this._handleDragOver(t,e)}
        @dragleave=${t=>this._handleDragLeave(t)}
        @drop=${t=>this._handleDrop(t,e)}
        @dragend=${this._handleDragEnd}
        @click=${()=>!this._editMode&&this._handleClick(t)}
      >
        <webrtc-player
          .go2rtcUrl=${this._go2rtcUrl}
          .streamId=${String(l)}
          .mode=${this._config.streaming_mode||"webrtc"}
          .orientation=${d}
          .videoWidth=${o}
          .videoHeight=${n}
        ></webrtc-player>

        <div class="monitor-overlay">
          ${this._config.show_motion_indicator&&_?q`
                <div class="motion-indicator">
                  <div class="motion-dot"></div>
                  <span>Motion Detected</span>
                </div>
              `:""}

          <div class="monitor-name">${g}</div>

          ${this._config.show_controls?q`
                <div class="controls">
                  <button
                    class="control-button"
                    @click=${e=>this._handleFullscreen(e,t)}
                    title="Fullscreen"
                  >
                    ⛶
                  </button>
                </div>
              `:""}
        </div>
      </div>
    `}_getAspectRatioCss(t,e,i){return i?`${e} / ${t}`:`${t} / ${e}`}_normalizeOrientation(t){switch(t){case"ROTATE_90":case"Rotate Right":return"ROTATE_90";case"ROTATE_180":case"Inverted":return"ROTATE_180";case"ROTATE_270":case"Rotate Left":return"ROTATE_270";default:return"ROTATE_0"}}_detectGo2rtcUrl(){if(this._config.zoneminder_go2rtc_url)this._go2rtcUrl=this._config.zoneminder_go2rtc_url;else for(const t of this._config.monitors){const e=this.hass.states[t.entity];if(e?.attributes.go2rtc_url)return void(this._go2rtcUrl=e.attributes.go2rtc_url)}}_handleClick(t){"fullscreen"===this._config.click_action?this._handleFullscreen(new Event("click"),t):"events"===this._config.click_action&&this._navigateToEvents(t)}_handleFullscreen(t,e){t.stopPropagation(),console.log("Fullscreen requested for",e.entity)}_handleDragStart(t,e){this._editMode&&(this._draggedIndex=e,t.dataTransfer&&(t.dataTransfer.effectAllowed="move",t.dataTransfer.setData("text/plain",String(e))),requestAnimationFrame(()=>{this.requestUpdate()}))}_handleDragOver(t,e){if(!this._editMode||null===this._draggedIndex)return;t.preventDefault(),t.dataTransfer&&(t.dataTransfer.dropEffect="move");const i=t.currentTarget;e!==this._draggedIndex&&i.classList.add("drag-over")}_handleDragLeave(t){t.currentTarget.classList.remove("drag-over")}_handleDrop(t,e){if(t.preventDefault(),!this._editMode||null===this._draggedIndex)return;t.currentTarget.classList.remove("drag-over"),this._draggedIndex!==e&&this._reorderMonitors(this._draggedIndex,e),this._draggedIndex=null}_handleDragEnd(){this._draggedIndex=null;const t=this.shadowRoot?.querySelectorAll(".drag-over");t?.forEach(t=>t.classList.remove("drag-over")),this.requestUpdate()}_reorderMonitors(t,e){const i=[...this._config.monitors],[s]=i.splice(t,1);i.splice(e,0,s);const r={...this._config,monitors:i};this._config=r,this._saveMonitorOrder(i);const o=new CustomEvent("config-changed",{detail:{config:r},bubbles:!0,composed:!0});this.dispatchEvent(o)}_navigateToEvents(t){console.log("Navigate to events for",t.entity)}static getConfigElement(){return document.createElement("zoneminder-card-editor")}static getStubConfig(){return{type:"custom:zoneminder-card",title:"Security Cameras",monitors:[{entity:"camera.front_door"},{entity:"camera.backyard"}],columns:4,streaming_mode:"webrtc",show_motion_indicator:!0}}};gt.styles=n`
    :host {
      display: block;
      padding: 16px;
    }

    .card-header {
      font-size: 24px;
      font-weight: 400;
      padding: 0 0 16px 0;
      color: var(--primary-text-color);
      font-family: var(--paper-font-headline_-_font-family);
    }

    .grid {
      display: grid;
      gap: 8px;
      width: 100%;
      grid-auto-flow: dense;
    }

    .monitor {
      position: relative;
      background: #000;
      border-radius: 4px;
      overflow: hidden;
      width: 100%;
    }

    .monitor.motion-active {
      outline: 3px solid var(--error-color, #ff5252);
      outline-offset: -3px;
      animation: pulse 2s ease-in-out infinite;
    }

    @keyframes pulse {
      0%, 100% {
        outline-color: var(--error-color, #ff5252);
      }
      50% {
        outline-color: rgba(255, 82, 82, 0.5);
      }
    }

    .monitor-overlay {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      pointer-events: none;
      z-index: 10;
    }

    .motion-indicator {
      position: absolute;
      top: 8px;
      left: 8px;
      background: var(--error-color, #ff5252);
      color: white;
      padding: 4px 12px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 6px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
      animation: fadeIn 0.3s ease-in-out;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(-4px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .motion-dot {
      width: 8px;
      height: 8px;
      background: white;
      border-radius: 50%;
      animation: blink 1s ease-in-out infinite;
    }

    @keyframes blink {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.3; }
    }

    .monitor-name {
      position: absolute;
      bottom: 8px;
      left: 8px;
      background: rgba(0, 0, 0, 0.7);
      color: white;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
    }

    .controls {
      position: absolute;
      bottom: 8px;
      right: 8px;
      display: flex;
      gap: 4px;
      pointer-events: auto;
    }

    .control-button {
      background: rgba(0, 0, 0, 0.7);
      color: white;
      border: none;
      border-radius: 4px;
      padding: 8px;
      cursor: pointer;
      transition: background 0.2s;
    }

    .control-button:hover {
      background: rgba(0, 0, 0, 0.9);
    }

    .control-button:active {
      transform: scale(0.95);
    }

    webrtc-player {
      width: 100%;
      height: 100%;
    }

    .error {
      padding: 16px;
      background: var(--error-color, #ff5252);
      color: white;
      border-radius: 4px;
      margin-bottom: 16px;
    }

    .warning {
      padding: 16px;
      background: var(--warning-color, #ff9800);
      color: white;
      border-radius: 4px;
      margin-bottom: 16px;
    }

    .header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .edit-toggle {
      background: var(--primary-color, #03a9f4);
      color: white;
      border: none;
      border-radius: 4px;
      padding: 8px 16px;
      font-size: 14px;
      cursor: pointer;
      transition: background 0.2s;
    }

    .edit-toggle:hover {
      background: var(--primary-color-dark, #0288d1);
    }

    .edit-toggle.active {
      background: var(--success-color, #4caf50);
    }

    .monitor.edit-mode {
      cursor: grab;
      outline: 2px dashed var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }

    .monitor.edit-mode:hover {
      outline-color: var(--accent-color, #ff9800);
    }

    .monitor.dragging {
      opacity: 0.5;
      cursor: grabbing;
    }

    .monitor.drag-over {
      outline: 3px solid var(--accent-color, #ff9800);
      outline-offset: 2px;
    }
  `,t([pt({attribute:!1})],gt.prototype,"hass",void 0),t([ut()],gt.prototype,"_config",void 0),t([ut()],gt.prototype,"_go2rtcUrl",void 0),t([ut()],gt.prototype,"_editMode",void 0),t([ut()],gt.prototype,"_draggedIndex",void 0),gt=t([ct("zoneminder-card")],gt);export{gt as ZoneMinerCard};
