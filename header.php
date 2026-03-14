<?php
/**
 * The template for displaying the header.
 *
 * @package GeneratePress
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

?><!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
	<meta charset="<?php bloginfo( 'charset' ); ?>">
	<?php wp_head(); ?>
</head>

<body <?php body_class(); ?> <?php generate_do_microdata( 'body' ); ?>>
	<?php
	/**
	 * wp_body_open hook.
	 *
	 * @since 2.3
	 */
	do_action( 'wp_body_open' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- core WP hook.
	?>
	<style>
	  #gsm-wrap{position:fixed;inset:0;z-index:9999;pointer-events:none}
	  #gsm-wrap.modal-open{pointer-events:all}
	  #gsm-wrap iframe{width:100%;height:100%;border:none;background:transparent;pointer-events:none}
	  #gsm-wrap.modal-open iframe{pointer-events:all}
	  #gsm-book-btn{
	    position:fixed;bottom:24px;right:24px;z-index:9998;
	    background:#8176FF;color:#F4EDFF;
	    font-family:'Montserrat',sans-serif;font-weight:700;font-size:.88rem;
	    border:none;border-radius:12px;padding:13px 20px;
	    cursor:pointer;display:flex;align-items:center;gap:8px;
	    box-shadow:0 0 20px rgba(129,118,255,.5),0 4px 16px rgba(0,0,0,.5);
	    pointer-events:all;
	    opacity:1;transform:translateY(0);
	    transition:opacity .3s ease,transform .3s ease;
	  }
	  #gsm-book-btn:hover{background:#9a91ff;box-shadow:0 0 28px rgba(129,118,255,.7),0 4px 20px rgba(0,0,0,.5)}
	  #gsm-wrap.modal-open #gsm-book-btn{opacity:0;pointer-events:none;transform:translateY(6px)}
	</style>
	<div id="gsm-wrap">
	  <iframe id="gsm-iframe" src="https://web-production-cd19.up.railway.app" allow="payment; popups" allowpaymentrequest sandbox="allow-scripts allow-forms allow-same-origin allow-popups allow-popups-to-escape-sandbox"></iframe>
	  <button id="gsm-book-btn">📱 Programeaza-te</button>
	</div>
	<script>
	  var _revTab=null,_revPoll=null;
	  document.getElementById("gsm-book-btn").addEventListener("click",function(){
	    var w=document.getElementById("gsm-wrap");
	    var ifr=document.getElementById("gsm-iframe");
	    w.classList.add("modal-open");
	    ifr.contentWindow.postMessage({action:"openBooking"},"https://web-production-cd19.up.railway.app");
	  });
	  <?php if(is_front_page()): ?>
	  document.getElementById("gsm-iframe").addEventListener("load",function(){
	    this.contentWindow.postMessage({action:"openBooking"},"https://web-production-cd19.up.railway.app");
	  });
	  <?php endif; ?>
	  window.addEventListener("message",function(e){
	    if(e.origin!=="https://web-production-cd19.up.railway.app")return;
	    if(!e.data||!e.data.action)return;
	    var w=document.getElementById("gsm-wrap");
	    var ifr=document.getElementById("gsm-iframe");
	    if(e.data.action==="closeBooking")w.classList.remove("modal-open");
	    if(e.data.action==="openBooking")w.classList.add("modal-open");
	    if(e.data.action==="revolutRedirect"&&e.data.url&&/^https:\/\/checkout\.revolut\.com\//.test(e.data.url)){
	      _revTab=window.open(e.data.url,"_blank");
	      if(_revPoll)clearInterval(_revPoll);
	      _revPoll=setInterval(function(){
	        if(_revTab&&_revTab.closed){clearInterval(_revPoll);_revPoll=null;ifr.contentWindow.postMessage({action:"revolutWindowClosed"},"https://web-production-cd19.up.railway.app");}
	      },500);
	    }
	    if(e.data.action==="closeRevolutTab"){
	      if(_revPoll){clearInterval(_revPoll);_revPoll=null;}
	      if(_revTab&&!_revTab.closed){_revTab.close();}
	      _revTab=null;
	    }
	    if(e.data.action==="paymentDone"){
	      ifr.contentWindow.postMessage(e.data,"https://web-production-cd19.up.railway.app");
	    }
	  });
	</script>
	<?php

	/**
	 * generate_before_header hook.
	 *
	 * @since 0.1
	 *
	 * @hooked generate_do_skip_to_content_link - 2
	 * @hooked generate_top_bar - 5
	 * @hooked generate_add_navigation_before_header - 5
	 */
	do_action( 'generate_before_header' );

	/**
	 * generate_header hook.
	 *
	 * @since 1.3.42
	 *
	 * @hooked generate_construct_header - 10
	 */
	do_action( 'generate_header' );

	/**
	 * generate_after_header hook.
	 *
	 * @since 0.1
	 *
	 * @hooked generate_featured_page_header - 10
	 */
	do_action( 'generate_after_header' );
	?>

	<div <?php generate_do_attr( 'page' ); ?>>
		<?php
		/**
		 * generate_inside_site_container hook.
		 *
		 * @since 2.4
		 */
		do_action( 'generate_inside_site_container' );
		?>
		<div <?php generate_do_attr( 'site-content' ); ?>>
			<?php
			/**
			 * generate_inside_container hook.
			 *
			 * @since 0.1
			 */
			do_action( 'generate_inside_container' );